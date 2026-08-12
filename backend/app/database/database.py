"""
Database connection and initialization.
"""
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import settings
from app.core.logger import get_logger
from app.database.base import Base

# Import all models so SQLAlchemy registers their tables before create_all.
from app import models  # noqa: F401

logger = get_logger(__name__)

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Create application tables and verify the database connection."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise


async def get_db():
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
