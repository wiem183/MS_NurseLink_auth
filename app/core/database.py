from collections.abc import AsyncGenerator

from sqlalchemy import create_engine  # ← ADD THIS
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker  # ← ADD sessionmaker

from app.core.config import settings

#this is app/core/database.py
# ---------------------------------------------------------------------------
# ASYNC Engine (for FastAPI)
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# SYNC Engine (for Alembic migrations)
# ---------------------------------------------------------------------------
# Convert async URL to sync URL
sync_database_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://",
    "postgresql://"
)

sync_engine = create_engine(
    sync_database_url,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""
    pass


# ---------------------------------------------------------------------------
# Async session dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async DB session and ensure it is closed afterwards.

    Usage in a router:
        async def endpoint(db: AsyncSession = Depends(get_db)): ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Sync session dependency (for Alembic)
# ---------------------------------------------------------------------------
def get_sync_db():
    """Sync DB session for Alembic migrations."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers for testing / Alembic migrations
# ---------------------------------------------------------------------------
async def create_all_tables() -> None:
    """Create all tables (useful in tests or local dev without Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """Drop all tables (useful in test teardown)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)