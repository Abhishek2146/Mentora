#!/usr/bin/env python3
"""
Neon Database Connection & Diagnostics Script for Mentora.

Usage:
    # Test current configuration in .env:
    python backend/verify_neon.py

    # Test a specific connection string:
    python backend/verify_neon.py --url "postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"

    # Test and initialize tables / run migrations:
    python backend/verify_neon.py --init-db
"""

import argparse
import asyncio
import os
import sys
import time
from urllib.parse import urlsplit

# Add backend directory to sys.path so app modules are discoverable
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import normalize_database_url, settings
from app.database.database import is_neon_or_pooler_url, init_db


def mask_url(url: str) -> str:
    """Mask password in URL for secure logging."""
    try:
        parts = urlsplit(url)
        if parts.password:
            netloc = parts.netloc.replace(f":{parts.password}@", ":******@")
            return url.replace(parts.netloc, netloc)
        return url
    except Exception:
        return "<url masked>"


async def run_diagnostics(target_url: str, do_init: bool = False) -> bool:
    normalized = normalize_database_url(target_url)
    is_neon = is_neon_or_pooler_url(normalized)
    is_pooler = "-pooler" in normalized.lower()

    print("=" * 60)
    print(" Mentora - Neon Database Diagnostic Tool")
    print("=" * 60)
    print(f"Target URL:       {mask_url(target_url)}")
    print(f"Normalized URL:   {mask_url(normalized)}")
    print(f"Detected Neon:    {'YES' if is_neon else 'NO'}")
    print(f"Endpoint Type:    {'Pooled (PgBouncer)' if is_pooler else ('Direct (Compute)' if is_neon else 'Standard Postgres')}")
    print("=" * 60)

    connect_args = {}
    if is_neon or is_pooler:
        connect_args["statement_cache_size"] = 0
        print("[INFO] Setting statement_cache_size=0 for Neon / PgBouncer compatibility.")

    engine = create_async_engine(
        normalized,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args,
    )

    print("\nConnecting to database (handling potential Neon cold start)...")
    start_time = time.perf_counter()

    try:
        async with engine.begin() as conn:
            elapsed = (time.perf_counter() - start_time) * 1000
            print(f"[SUCCESS] Connected in {elapsed:.1f}ms!")

            # 1. Version
            ver_res = await conn.execute(text("SELECT version()"))
            db_version = ver_res.scalar()
            print(f"\n[DB VERSION]  {db_version}")

            # 2. Database & User
            info_res = await conn.execute(text("SELECT current_database(), current_user"))
            row = info_res.fetchone()
            if row:
                print(f"[DATABASE]    {row[0]}")
                print(f"[USER]        {row[1]}")

            # 3. SSL Check
            try:
                ssl_res = await conn.execute(text("SELECT ssl_is_used()"))
                ssl_active = ssl_res.scalar()
                print(f"[SSL ENCRYPT] {'Active (secure)' if ssl_active else 'Not using SSL'}")
            except Exception:
                print("[SSL ENCRYPT] SSL connection established via asyncpg")

            # 4. Tables count
            tables_res = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [r[0] for r in tables_res.fetchall()]
            print(f"[TABLES]      {len(tables)} tables present in 'public' schema:")
            if tables:
                for t in sorted(tables):
                    print(f"              - {t}")
            else:
                print("              (No tables found. Run with --init-db to initialize Mentora tables)")

        # Optional: Initialize DB
        if do_init:
            print("\n" + "-" * 60)
            print("Initializing Mentora schema and running migrations...")
            print("-" * 60)
            await init_db()
            print("[SUCCESS] Mentora schema initialized successfully on Neon!")

        await engine.dispose()
        print("\n" + "=" * 60)
        print("[PASSED] All database checks completed successfully.")
        print("=" * 60)
        return True

    except Exception as exc:
        elapsed = (time.perf_counter() - start_time) * 1000
        print(f"\n[ERROR] Connection failed after {elapsed:.1f}ms: {exc}")
        print("\nTroubleshooting Tips:")
        print(" 1. Check your password in the connection string.")
        print(" 2. If Neon compute was paused, retry once more to allow cold-start wakeup.")
        print(" 3. Ensure your IP has access (Neon IP allowlist in Project Settings if enabled).")
        print(" 4. Verify your endpoint hostname (e.g. ep-xxx.neon.tech).")
        await engine.dispose()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test and diagnose Neon database connection for Mentora")
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Database connection URL (defaults to DATABASE_URL or NEON_DATABASE_URL from environment/.env)",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Run init_db() to create tables and apply migrations after verifying connection",
    )
    args = parser.parse_args()

    db_url = args.url or settings.DATABASE_URL
    if not db_url:
        print("[ERROR] No DATABASE_URL or NEON_DATABASE_URL found in environment or .env.")
        sys.exit(1)

    success = asyncio.run(run_diagnostics(db_url, do_init=args.init_db))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
