"""Database adapter — Supabase (PostgreSQL) with local SQLite fallback.

When ``SUPABASE_DB_URL`` is configured → uses Agno's ``PostgresDb``.
Otherwise → uses a local SQLite file for zero-config development.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

from src.config.settings import Settings

logger = logging.getLogger(__name__)


def get_database(settings: Settings) -> Union["PostgresDb", "SqliteDb"]:  # type: ignore[name-defined]
    """Return an Agno-compatible database backend based on configuration."""

    if settings.supabase_db_url:
        from agno.db.postgres import PostgresDb

        logger.info("Database: Supabase (PostgreSQL)")
        return PostgresDb(db_url=settings.supabase_db_url)

    # ── Fallback: SQLite ────────────────────────────────────────
    db_dir = settings.project_root / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = str(db_dir / "devteam.db")

    from agno.db.sqlite import SqliteDb

    logger.info("Database: SQLite → %s", db_file)
    return SqliteDb(db_file=db_file)
