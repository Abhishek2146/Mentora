"""
Database connection and initialization
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


# --------------------------------------------------
# Database Engine
# --------------------------------------------------

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)


# --------------------------------------------------
# Async Session
# --------------------------------------------------

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# --------------------------------------------------
# Schema Migration
# --------------------------------------------------

async def _run_migrations(conn) -> None:
    """Idempotently add columns to existing tables that are defined in
    the SQLAlchemy models but missing from the live database.

    ``Base.metadata.create_all`` only creates tables that do not yet
    exist; it never alters existing tables.  This helper bridges that
    gap so model changes (e.g. adding ``estimated_hours`` to
    ``chapters``) are applied without a separate migration tool.
    """
    # Iterate over every registered model and check each column.
    for table in Base.metadata.tables.values():
        table_name = table.name
        for column in table.columns:
            # Skip base columns (id, created_at, updated_at) which are
            # always present on existing tables.
            if column.name in ("id", "created_at", "updated_at"):
                continue

            result = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ).bindparams(t=table_name, c=column.name)
            )
            if result.fetchone():
                continue  # column already exists

            # Build the DDL fragment for this column.
            col_type = str(column.type)
            parts = [f'"{column.name}"', col_type]

            # Server-side default (e.g. DEFAULT 0).
            if column.server_default is not None:
                parts.append(f"DEFAULT {column.server_default}")
            elif column.default is not None and column.default.is_callable is False:
                parts.append(f"DEFAULT {column.default.arg}")

            # Nullability.
            if not column.nullable and "DEFAULT" not in parts:
                # If a default is provided, allow NOT NULL to use it.
                # If no default, make it nullable to avoid breaking
                # existing rows.
                if "DEFAULT" in parts:
                    parts.append("NOT NULL")
                else:
                    # No default and not nullable — still add as nullable
                    # so existing rows don't break; the app default 0
                    # will be applied on read.
                    pass
            elif not column.nullable:
                parts.append("NOT NULL")

            ddl = "ALTER TABLE " + f'"{table_name}"' + " ADD COLUMN " + " ".join(parts)
            await conn.execute(text(ddl))
            logger.info(
                "Added column '%s' to table '%s'",
                column.name,
                table_name,
            )


# --------------------------------------------------
# Initialize Database
# --------------------------------------------------

async def init_db() -> None:
    """Create application tables and verify the database connection."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
            await _run_migrations(conn)
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise


# --------------------------------------------------
# Database Dependency
# --------------------------------------------------

async def get_db():
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
