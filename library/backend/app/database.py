"""
SmartLib Kiosk - Database Connection and Session Management
Configured for Supabase PostgreSQL
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import settings


# Create async engine for Supabase PostgreSQL
# Using NullPool for serverless/connection pooler compatibility
# - For asyncpg: disable prepared statement cache for pgbouncer transaction mode
# - For psycopg3: set prepare_threshold=0 to disable server-side prepared statements
_db_url = settings.database_url or ""
_connect_args: dict = {}
if "postgresql+asyncpg://" in _db_url:
    _connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
elif "postgresql+psycopg_async://" in _db_url or "postgresql+psycopg://" in _db_url:
    _connect_args = {
        "prepare_threshold": 0,
    }

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    poolclass=NullPool,  # Important for Supabase/pgbouncer pooler
    connect_args=_connect_args,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.
    Usage in FastAPI endpoints:
        async def endpoint(db: AsyncSession = Depends(get_db)):
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database connection.
    
    Note: For Supabase with pgbouncer, we skip table creation since:
    1. Tables already exist in Supabase
    2. pgbouncer in transaction mode has issues with prepared statements
    
    We only test basic connectivity here.
    """
    try:
        # Test basic connectivity with a simple query
        from sqlalchemy import text
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            await session.commit()
    except Exception as e:
        # Log but don't fail - tables already exist in Supabase
        import logging
        logging.warning(f"Database init check: {e}")


async def close_db():
    """Close database connection."""
    await engine.dispose()
