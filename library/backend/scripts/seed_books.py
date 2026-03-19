"""
Seed books into the database using Google Books API.

Usage (from backend/):
    python scripts/seed_books.py

Optional env vars:
    - GOOGLE_BOOKS_API_KEY: Google Books API key (recommended for higher quota)
    - SEED_LIMIT: int, max number of books to insert (default: all queries)
    - SEED_COVERS: "1" to download covers (default: 1)
"""

from __future__ import annotations

import asyncio
import os
import random
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger
from sqlalchemy import text

# Ensure imports work when running as a script
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Load .env BEFORE importing app.config/app.database (settings are created at import time)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(BACKEND_ROOT / ".env")
except Exception:
    # Seeding can still run if env vars are set externally.
    pass

from app.database import async_session_maker  # noqa: E402


GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
STATIC_COVERS_DIR = BACKEND_ROOT / "static" / "covers"


BOOK_QUERIES: list[str] = [
    # ISBN queries (fast + accurate)
    "isbn:9780132350884",  # Clean Code
    "isbn:9780134685991",  # Effective Java
    "isbn:9781492056355",  # Designing Data-Intensive Applications (varies by edition)
    "isbn:9780201633610",  # Design Patterns
    "isbn:9780134494166",  # Clean Architecture
    "isbn:9781617296086",  # Spring in Action (varies by edition)
    # Popular IT/Programming titles (fallback)
    "The Pragmatic Programmer",
    "Refactoring Martin Fowler",
    "Introduction to Algorithms CLRS",
    "You Don't Know JS",
    "Python Crash Course",
    "Eloquent JavaScript",
    "Head First Design Patterns",
    "Grokking Algorithms",
    "Docker Deep Dive",
]


@dataclass(frozen=True)
class GoogleBookVolume:
    title: Optional[str]
    authors: list[str]
    publisher: Optional[str]
    published_year: Optional[int]
    language: Optional[str]
    page_count: Optional[int]
    description: Optional[str]
    isbn_13: Optional[str]
    thumbnail_url: Optional[str]


def _safe_year(published_date: Optional[str]) -> Optional[int]:
    if not published_date:
        return None
    # formats: "YYYY", "YYYY-MM-DD", "YYYY-MM"
    m = re.match(r"^\s*(\d{4})", published_date)
    if not m:
        return None
    try:
        year = int(m.group(1))
        if 1400 <= year <= 2100:
            return year
    except ValueError:
        return None
    return None


def _extract_isbn13(industry_identifiers: Any) -> Optional[str]:
    if not isinstance(industry_identifiers, list):
        return None
    for ident in industry_identifiers:
        if not isinstance(ident, dict):
            continue
        if ident.get("type") == "ISBN_13" and isinstance(ident.get("identifier"), str):
            return ident["identifier"].strip()
    return None


def _parse_volume(item: dict[str, Any]) -> GoogleBookVolume:
    volume_info = item.get("volumeInfo") or {}
    title = volume_info.get("title")
    authors = volume_info.get("authors") or []
    if not isinstance(authors, list):
        authors = []
    authors = [a for a in authors if isinstance(a, str)]

    publisher = volume_info.get("publisher")
    published_year = _safe_year(volume_info.get("publishedDate"))
    language = volume_info.get("language")
    page_count = volume_info.get("pageCount")
    if not isinstance(page_count, int):
        page_count = None
    description = volume_info.get("description")

    isbn_13 = _extract_isbn13(volume_info.get("industryIdentifiers"))

    image_links = volume_info.get("imageLinks") or {}
    thumbnail_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
    if isinstance(thumbnail_url, str):
        thumbnail_url = thumbnail_url.replace("http://", "https://").strip()
    else:
        thumbnail_url = None

    return GoogleBookVolume(
        title=title if isinstance(title, str) else None,
        authors=authors,
        publisher=publisher if isinstance(publisher, str) else None,
        published_year=published_year,
        language=language if isinstance(language, str) else None,
        page_count=page_count,
        description=description if isinstance(description, str) else None,
        isbn_13=isbn_13,
        thumbnail_url=thumbnail_url,
    )


def _generate_barcode(existing: set[str]) -> str:
    # 12-digit mock barcode (EAN-13 without checksum), good enough for demo
    while True:
        barcode = "".join(str(random.randint(0, 9)) for _ in range(12))
        if barcode not in existing:
            existing.add(barcode)
            return barcode


def _cover_ext_from_content_type(content_type: Optional[str]) -> str:
    if not content_type:
        return ".jpg"
    ct = content_type.split(";")[0].strip().lower()
    if ct == "image/png":
        return ".png"
    if ct in ("image/jpeg", "image/jpg"):
        return ".jpg"
    if ct == "image/webp":
        return ".webp"
    return ".jpg"


async def _download_cover(
    client: httpx.AsyncClient,
    thumbnail_url: str,
    book_id: str,
) -> Optional[str]:
    STATIC_COVERS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        resp = await client.get(thumbnail_url, timeout=20)
        if resp.status_code != 200 or not resp.content:
            return None
        ext = _cover_ext_from_content_type(resp.headers.get("content-type"))
        filename = f"{book_id}{ext}"
        out_path = STATIC_COVERS_DIR / filename
        out_path.write_bytes(resp.content)
        # Store relative path from backend root (as used by app)
        return str(Path("static") / "covers" / filename).replace("\\", "/")
    except Exception as e:
        logger.warning(f"Cover download failed for {book_id}: {e}")
        return None


async def _fetch_first_volume(
    client: httpx.AsyncClient,
    query: str,
    api_key: Optional[str],
) -> Optional[GoogleBookVolume]:
    params = {"q": query, "maxResults": 1, "printType": "books"}
    if api_key:
        params["key"] = api_key
    # Handle 429 with backoff (common without API key)
    retries = 4
    backoff_s = 0.8
    for attempt in range(1, retries + 1):
        try:
            resp = await client.get(GOOGLE_BOOKS_URL, params=params, timeout=20)
            if resp.status_code == 429:
                if attempt == retries:
                    logger.warning(f"Google Books rate limited (429) for query={query!r}. Giving up after {retries} tries.")
                    return None
                sleep_s = backoff_s * (2 ** (attempt - 1)) + random.random() * 0.25
                logger.warning(f"Google Books rate limited (429) for query={query!r}. Retrying in {sleep_s:.2f}s (attempt {attempt}/{retries}).")
                await asyncio.sleep(sleep_s)
                continue

            resp.raise_for_status()
            payload = resp.json()
            items = payload.get("items") or []
            if not items:
                return None
            if not isinstance(items, list) or not isinstance(items[0], dict):
                return None
            return _parse_volume(items[0])
        except httpx.HTTPStatusError as e:
            logger.warning(f"Google Books HTTP error for query={query!r}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Google Books fetch failed for query={query!r}: {e}")
            return None
    return None


async def _book_exists(db, *, isbn_13: Optional[str], title: Optional[str]) -> bool:
    """
    Duplicate guard without importing ORM models.
    Keeps this script runnable even if unrelated model deps are missing.
    """
    if isbn_13:
        res = await db.execute(
            text("SELECT 1 FROM books WHERE isbn_13 = :isbn_13 LIMIT 1"),
            {"isbn_13": isbn_13},
        )
        if res.first() is not None:
            return True

    if title:
        res = await db.execute(
            text("SELECT 1 FROM books WHERE lower(title) = lower(:title) LIMIT 1"),
            {"title": title},
        )
        if res.first() is not None:
            return True

    return False


async def _insert_book(db, values: dict[str, Any]) -> None:
    """
    Insert into books table using SQL to avoid ORM mapper initialization issues.
    """
    await db.execute(
        text(
            """
            INSERT INTO books (
                book_id,
                title,
                author,
                isbn_13,
                barcode,
                publisher,
                publication_year,
                language,
                pages,
                description,
                cover_image_path,
                status
            ) VALUES (
                :book_id,
                :title,
                :author,
                :isbn_13,
                :barcode,
                :publisher,
                :publication_year,
                :language,
                :pages,
                :description,
                :cover_image_path,
                :status
            )
            """
        ),
        values,
    )


async def seed_books() -> int:
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY") or None
    seed_limit_raw = os.getenv("SEED_LIMIT", "").strip()
    seed_limit = int(seed_limit_raw) if seed_limit_raw.isdigit() else None
    seed_covers = os.getenv("SEED_COVERS", "1").strip() != "0"
    delay_ms_raw = os.getenv("SEED_DELAY_MS", "250").strip()
    delay_ms = int(delay_ms_raw) if delay_ms_raw.isdigit() else 250

    queries = BOOK_QUERIES[: seed_limit] if seed_limit else BOOK_QUERIES

    logger.info(f"Seeding books from Google Books API. queries={len(queries)} covers={'on' if seed_covers else 'off'}")
    if not api_key:
        logger.info("GOOGLE_BOOKS_API_KEY is not set. Proceeding without an API key (lower quota).")

    inserted = 0
    used_barcodes: set[str] = set()

    async with httpx.AsyncClient(headers={"User-Agent": "SmartLibSeeder/1.0"}) as client:
        async with async_session_maker() as db:
            for idx, query in enumerate(queries, start=1):
                logger.info(f"[{idx}/{len(queries)}] Fetching: {query!r}")
                vol = await _fetch_first_volume(client, query, api_key)
                if not vol or not vol.title:
                    logger.warning(f"[{idx}/{len(queries)}] No result for query: {query!r}")
                    continue

                try:
                    if await _book_exists(db, isbn_13=vol.isbn_13, title=vol.title):
                        logger.info(f"[{idx}/{len(queries)}] Skipping existing book: {vol.title!r}")
                        continue

                    book_uuid = uuid.uuid4().hex
                    book_id = f"BK-{book_uuid[:12].upper()}"
                    barcode = _generate_barcode(used_barcodes)

                    cover_path = None
                    if seed_covers and vol.thumbnail_url:
                        cover_path = await _download_cover(client, vol.thumbnail_url, book_id)

                    await _insert_book(
                        db,
                        {
                            "book_id": book_id,
                            "title": vol.title,
                            "author": ", ".join(vol.authors) if vol.authors else None,
                            "isbn_13": vol.isbn_13,
                            "barcode": barcode,
                            "publisher": vol.publisher,
                            "publication_year": vol.published_year,
                            "language": vol.language or "en",
                            "pages": vol.page_count,
                            "description": vol.description,
                            "cover_image_path": cover_path,
                            "status": "AVAILABLE",
                        },
                    )
                    await db.commit()
                    inserted += 1
                    logger.success(f"[{idx}/{len(queries)}] Inserted: {vol.title!r} (book_id={book_id}, isbn13={vol.isbn_13})")
                except Exception as e:
                    await db.rollback()
                    logger.error(f"[{idx}/{len(queries)}] Failed insert for query={query!r}: {e}")
                    continue

                # Gentle pacing to reduce rate-limits
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000)

    logger.info(f"Done. Inserted {inserted} books.")
    return inserted


def main() -> None:
    try:
        asyncio.run(seed_books())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")


if __name__ == "__main__":
    main()

