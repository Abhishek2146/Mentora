"""
Database session management
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.database import engine

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        async with session.begin():
            yield session


async def get_session_no_commit() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
