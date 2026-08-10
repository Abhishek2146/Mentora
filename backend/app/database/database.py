"""
Database connection and initialization
"""
import asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings
from app.core.logger import get_logger

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
    autocommit=False,
)

Base = declarative_base()


async def init_db():
    """Initialize database - create tables if using SQLite, ensure connection for PostgreSQL."""
    if "sqlite" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite database tables created")
    else:
        try:
            conn = await asyncpg.connect(settings.DATABASE_URL)
            await conn.close()
            logger.info("PostgreSQL database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
