"""
SmartLib Kiosk - Database Models Package
"""
from typing import TYPE_CHECKING

# Avoid eager imports here.
# Importing this package should not force-import optional/heavy deps (e.g. pgvector).
#
# Prefer importing models directly:
#   from app.models.book import Book
#   from app.models.student import Student
#
# This keeps scripts and tooling (seeding, migrations, etc.) more robust.

if TYPE_CHECKING:  # pragma: no cover
    from app.models.student import Student  # noqa: F401
    from app.models.book import Book  # noqa: F401
    from app.models.transaction import Transaction  # noqa: F401
    from app.models.face_embedding import FaceEmbedding  # noqa: F401
    from app.models.audit_log import AuditLog  # noqa: F401

__all__ = ["Student", "Book", "Transaction", "FaceEmbedding", "AuditLog"]
