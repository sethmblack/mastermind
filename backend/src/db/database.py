"""Database connection and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import os

from ..config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def init_db() -> None:
    """Initialize the database, creating all tables."""
    # Ensure data directory exists
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    async with engine.begin() as conn:
        # Import models to ensure they're registered
        from . import models  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
