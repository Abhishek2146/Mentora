"""
Database connection and initialization
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import settings
from app.core.logger import get_logger
from app.database.base import Base

# Import all models so SQLAlchemy registers their tables before create_all.
from app import models  # noqa: F401

logger = get_logger(__name__)


def is_neon_or_pooler_url(url: str) -> bool:
    """Check if the database URL points to a Neon or PgBouncer pooled endpoint."""
    lowered = (url or "").lower()
    return "neon.tech" in lowered or "-pooler" in lowered or "pooler" in lowered


# --------------------------------------------------
# Database Engine
# --------------------------------------------------

def create_db_engine() -> AsyncEngine:
    """Create and configure the SQLAlchemy AsyncEngine with Neon / serverless optimizations."""
    is_sqlite = "sqlite" in settings.DATABASE_URL.lower()
    is_neon_or_pooler = is_neon_or_pooler_url(settings.DATABASE_URL)

    if is_sqlite:
        return create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
        )

    connect_args = {}

    # When connecting to Neon (especially through its PgBouncer pooler endpoint),
    # asyncpg's prepared statement caching causes DuplicatePreparedStatementError
    # across pooled transactions. Disabling statement cache (statement_cache_size=0)
    # is the officially recommended Neon and asyncpg configuration.
    if settings.DB_STATEMENT_CACHE_SIZE is not None:
        connect_args["statement_cache_size"] = settings.DB_STATEMENT_CACHE_SIZE
    elif is_neon_or_pooler:
        logger.info("Neon / PgBouncer pooler detected: setting statement_cache_size=0 for asyncpg.")
        connect_args["statement_cache_size"] = 0

    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        connect_args=connect_args,
    )


engine: AsyncEngine = create_db_engine()


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

async def _provision_pro_for_existing_users(conn) -> None:
    """Upgrade legacy Free subscriptions and backfill Pro for users without a row."""
    from app.models.subscription import (
        BillingCycle,
        PlanType,
        SubscriptionStatus,
    )

    upgraded = await conn.execute(
        text(
            """
            UPDATE subscriptions
            SET plan_type = :plan_type,
                billing_cycle = :billing_cycle,
                status = :status,
                expires_at = NULL
            WHERE plan_type = :free_plan
               OR status IN (:expired_status, :cancelled_status)
            """
        ).bindparams(
            plan_type=PlanType.SUBSCRIPTION.value,
            billing_cycle=BillingCycle.MONTHLY.value,
            status=SubscriptionStatus.ACTIVE.value,
            free_plan=PlanType.FREE.value,
            expired_status=SubscriptionStatus.EXPIRED.value,
            cancelled_status=SubscriptionStatus.CANCELLED.value,
        )
    )

    inserted = await conn.execute(
        text(
            """
            INSERT INTO subscriptions (
                user_id,
                plan_type,
                billing_cycle,
                status,
                started_at,
                auto_renew,
                created_at
            )
            SELECT
                u.id,
                :plan_type,
                :billing_cycle,
                :status,
                NOW(),
                FALSE,
                NOW()
            FROM users u
            LEFT JOIN subscriptions s ON s.user_id = u.id
            WHERE s.id IS NULL
            """
        ).bindparams(
            plan_type=PlanType.SUBSCRIPTION.value,
            billing_cycle=BillingCycle.MONTHLY.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
    )

    upgraded_count = upgraded.rowcount or 0
    inserted_count = inserted.rowcount or 0
    if upgraded_count or inserted_count:
        logger.info(
            "Provisioned Mentora Pro for existing users "
            "(upgraded=%s, created=%s)",
            upgraded_count,
            inserted_count,
        )


async def _migrate_user_roles(conn) -> None:
    """Ensure the users.role column accepts 'super_admin'.

    PostgreSQL ENUM columns require ALTER TYPE to add new values.
    This is idempotent — it checks before adding.
    """
    result = await conn.execute(
        text(
            "SELECT t.typname, e.enumlabel "
            "FROM pg_type t "
            "JOIN pg_enum e ON t.oid = e.enumtypid "
            "WHERE t.typname = 'userrole'"
        )
    )
    rows = result.fetchall()

    if rows:
        # Column is a PostgreSQL ENUM type — add super_admin if missing.
        existing_labels = {row[1] for row in rows}
        if "super_admin" not in existing_labels:
            await conn.execute(
                text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin'")
            )
            logger.info("Added 'super_admin' to userrole ENUM type")
    else:
        # Column is VARCHAR (not an ENUM type) — no DDL needed.
        # The Python enum handles validation; existing rows keep their values.
        pass


async def _fix_column_types(conn) -> None:
    """Upgrade specific columns that were created with an incorrect VARCHAR(255)
    type and need to be TEXT to handle long AI-generated content.

    This is idempotent: it checks the current column type before issuing
    any ALTER TABLE so it is safe to run on every startup.
    """
    upgrades = [
        # table_name, column_name
        ("study_tasks", "description"),
        ("study_plans", "description"),
        ("notes", "content"),
        ("notes", "ai_summary"),
    ]
    for table_name, column_name in upgrades:
        result = await conn.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ).bindparams(t=table_name, c=column_name)
        )
        row = result.fetchone()
        if row is None:
            continue  # column doesn't exist yet
        current_type = (row[0] or "").lower()
        if "character varying" in current_type or current_type == "varchar":
            await conn.execute(
                text(
                    f'ALTER TABLE "{table_name}" '
                    f'ALTER COLUMN "{column_name}" TYPE TEXT'
                )
            )
            logger.info(
                "Upgraded column '%s.%s' from VARCHAR to TEXT",
                table_name,
                column_name,
            )


async def _run_migrations(conn) -> None:
    """Idempotently add columns to existing tables that are defined in
    the SQLAlchemy models but missing from the live database.

    ``Base.metadata.create_all`` only creates tables that do not yet
    exist; it never alters existing tables.  This helper bridges that
    gap so model changes (e.g. adding ``estimated_hours`` to
    ``chapters``) are applied without a separate migration tool.
    """
    # Columns handled by specific migrations below — skip in the generic loop.
    _specific_migration_columns = {
        ("study_groups", "memory"),
        ("notes", "font_style"),
        ("study_group_messages", "edited_at"),
        ("study_group_messages", "deleted_at"),
        ("study_group_messages", "reply_to_message_id"),
        ("study_group_messages", "forwarded_from_id"),
    }

    # Iterate over every registered model and check each column.
    for table in Base.metadata.tables.values():
        table_name = table.name
        for column in table.columns:
            # Skip base columns (id, created_at, updated_at) which are
            # always present on existing tables.
            if column.name in ("id", "created_at", "updated_at"):
                continue

            # Skip columns handled by specific migrations.
            if (table_name, column.name) in _specific_migration_columns:
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

    # Specific migration for JSONB columns that the generic handler may not
    # produce valid DDL for (DefaultClause.__str__ wraps the value).
    jsonb_migrations = [
        (
            "study_groups",
            "memory",
            "ALTER TABLE study_groups ADD COLUMN IF NOT EXISTS memory JSONB NOT NULL DEFAULT '{}'::jsonb",
        ),
    ]
    for table_name, col_name, ddl in jsonb_migrations:
        result = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ).bindparams(t=table_name, c=col_name),
        )
        if not result.fetchone():
            await conn.execute(text(ddl))
            logger.info("Added JSONB column '%s' to table '%s'", col_name, table_name)

    # Specific migration for the notes font_style column so the string
    # default is properly quoted (the generic handler would emit an
    # unquoted, invalid DEFAULT for string defaults).
    string_default_migrations = [
        (
            "notes",
            "font_style",
            "ALTER TABLE notes ADD COLUMN IF NOT EXISTS font_style VARCHAR(50) NOT NULL DEFAULT 'inter'",
        ),
    ]
    for table_name, col_name, ddl in string_default_migrations:
        result = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ).bindparams(t=table_name, c=col_name),
        )
        if not result.fetchone():
            await conn.execute(text(ddl))
            logger.info("Added column '%s' to table '%s'", col_name, table_name)

    # Migration: add invite_token column to study_groups
    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'study_groups' AND column_name = 'invite_token'"
        )
    )
    if not result.fetchone():
        await conn.execute(
            text(
                "ALTER TABLE study_groups ADD COLUMN invite_token VARCHAR(64) UNIQUE"
            )
        )
        logger.info("Added invite_token column to study_groups")

        # Backfill existing groups with tokens
        import secrets
        rows = await conn.execute(text("SELECT id FROM study_groups WHERE invite_token IS NULL"))
        for row in rows.fetchall():
            token = secrets.token_urlsafe(32)
            await conn.execute(
                text("UPDATE study_groups SET invite_token = :token WHERE id = :id"),
                {"token": token, "id": row[0]},
            )
        logger.info("Backfilled invite_token for existing study_groups")

    # Migration: make invite_code nullable (old system kept for backward compat)
    result = await conn.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'study_groups' AND column_name = 'invite_code'"
        )
    )
    row = result.fetchone()
    if row and row[0].upper() == "NO":
        await conn.execute(
            text("ALTER TABLE study_groups ALTER COLUMN invite_code DROP NOT NULL")
        )
        logger.info("Made invite_code column nullable in study_groups")

    # Migration: add messenger-like feature columns to study_group_messages
    msg_columns = [
        ("edited_at", "ALTER TABLE study_group_messages ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ"),
        ("deleted_at", "ALTER TABLE study_group_messages ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ"),
        ("reply_to_message_id", "ALTER TABLE study_group_messages ADD COLUMN IF NOT EXISTS reply_to_message_id INTEGER REFERENCES study_group_messages(id) ON DELETE SET NULL"),
        ("forwarded_from_id", "ALTER TABLE study_group_messages ADD COLUMN IF NOT EXISTS forwarded_from_id INTEGER REFERENCES study_group_messages(id) ON DELETE SET NULL"),
    ]
    for col_name, ddl in msg_columns:
        result = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'study_group_messages' AND column_name = :c"
            ).bindparams(c=col_name),
        )
        if not result.fetchone():
            await conn.execute(text(ddl))
            logger.info("Added column '%s' to study_group_messages", col_name)


async def _ensure_unique_constraints(conn) -> None:
    """Idempotently add unique constraints that are defined in models
    but may be missing from existing tables."""
    # study_group_members: unique (group_id, user_id)
    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = 'study_group_members' "
            "AND constraint_name = 'uq_study_group_member_group_user'"
        )
    )
    if not result.fetchone():
        await conn.execute(
            text(
                "ALTER TABLE study_group_members "
                "ADD CONSTRAINT uq_study_group_member_group_user "
                "UNIQUE (group_id, user_id)"
            )
        )
        logger.info("Added unique constraint uq_study_group_member_group_user")

    # Column-level UNIQUE constraints are case-sensitive in PostgreSQL. These
    # expression indexes make the identity rule durable for requests that race
    # past the application-level duplicate lookup (and cover legacy schemas).
    if conn.dialect.name == "postgresql":
        for index_name, expression in (
            ("uq_users_email_lower", "LOWER(email)"),
            ("uq_users_username_lower", "LOWER(username)"),
        ):
            try:
                await conn.execute(
                    text(
                        f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
                        f"ON users ({expression})"
                    )
                )
                logger.info("Ensured unique identity index %s", index_name)
            except Exception as exc:
                # Existing case-variant duplicates must not be deleted or
                # silently changed during startup. The API lookup still
                # rejects all future duplicates until the legacy rows are
                # manually reconciled and the index can be created.
                logger.error(
                    "Could not create %s. Resolve existing duplicate users "
                    "before enabling the database index: %s",
                    index_name,
                    exc,
                )


async def _fix_broken_timestamps(conn) -> None:
    """Fix study_group_messages timestamps that were created with the broken
    server_default='now()' string literal.  Messages within each group that
    all share the exact same timestamp are spaced out 1 minute apart based
    on their id order so the chat timeline looks realistic."""
    # First, fix the column defaults on existing tables so new rows get proper now()
    alter_sqls = [
        "ALTER TABLE study_group_messages ALTER COLUMN created_at SET DEFAULT now()",
        "ALTER TABLE study_group_messages ALTER COLUMN updated_at SET DEFAULT now()",
        "ALTER TABLE study_groups ALTER COLUMN created_at SET DEFAULT now()",
        "ALTER TABLE study_groups ALTER COLUMN updated_at SET DEFAULT now()",
        "ALTER TABLE study_group_members ALTER COLUMN joined_at SET DEFAULT now()",
    ]
    for sql in alter_sqls:
        try:
            await conn.execute(text(sql))
        except Exception:
            pass  # column may not exist yet or default already correct

    # Check if there are any messages at all
    count_result = await conn.execute(text("SELECT COUNT(*) FROM study_group_messages"))
    total = count_result.scalar()
    if total == 0:
        return

    # Find groups where all messages share the same created_at (broken default)
    result = await conn.execute(
        text(
            """
            SELECT group_id, COUNT(*) as msg_count, MIN(created_at) as shared_ts
            FROM study_group_messages
            GROUP BY group_id
            HAVING COUNT(DISTINCT created_at) = 1 AND COUNT(*) > 1
            """
        )
    )
    broken_groups = result.fetchall()
    if not broken_groups:
        return

    for group_id, msg_count, shared_ts in broken_groups:
        # Update each message: space them 1 minute apart based on id order
        rows = await conn.execute(
            text(
                "SELECT id FROM study_group_messages "
                "WHERE group_id = :gid ORDER BY id ASC"
            ).bindparams(gid=group_id),
        )
        msg_ids = [r[0] for r in rows.fetchall()]
        for idx, msg_id in enumerate(msg_ids):
            offset = len(msg_ids) - 1 - idx
            await conn.execute(
                text(
                    f"UPDATE study_group_messages "
                    f"SET created_at = NOW() - INTERVAL '{offset} minutes', "
                    f"updated_at = NOW() - INTERVAL '{offset} minutes' "
                    f"WHERE id = {msg_id}"
                ),
            )
        logger.info(
            "Fixed %s broken timestamps in group %s", msg_count, group_id
        )


# --------------------------------------------------
# Initialize Database
# --------------------------------------------------

async def init_db(max_retries: int = 3, retry_delay: float = 2.0) -> None:
    """Create application tables and verify the database connection.

    Includes retry logic to gracefully accommodate Neon serverless cold starts
    (when compute wakes up from scale-to-zero suspension).
    """
    is_neon = is_neon_or_pooler_url(settings.DATABASE_URL)
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        try:
            if is_neon and attempt > 1:
                logger.info(
                    "Connecting to Neon database (attempt %d/%d, compute may be waking up)...",
                    attempt,
                    max_retries,
                )
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)
                await _fix_column_types(conn)
                await _run_migrations(conn)
                await _ensure_unique_constraints(conn)
                await _fix_broken_timestamps(conn)
                await _provision_pro_for_existing_users(conn)
                await _migrate_user_roles(conn)
            logger.info("Database initialized successfully")
            return
        except Exception as exc:
            if attempt < max_retries:
                logger.warning(
                    "Database connection attempt %d/%d failed (%s). Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    exc,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.exception(
                    "Database initialization failed after %d attempts: %s",
                    max_retries,
                    exc,
                )
                raise


# --------------------------------------------------
# Database Dependency
# --------------------------------------------------

async def get_db():
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
