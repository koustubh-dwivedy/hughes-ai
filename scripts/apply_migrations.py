"""HUG-253: apply migrations/*.sql against a Postgres database.

Replacement for the Makefile's `migrate` target when the database is not a
local docker-compose container (e.g., Cloud SQL via Auth Proxy). Reads
DATABASE_URL from env, opens a single connection, runs each migration in
order inside its own transaction.

The migrations are idempotent (every CREATE uses IF NOT EXISTS, every ALTER
guards against re-application). Safe to re-run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
import structlog

log = structlog.get_logger()

_REPO = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _REPO / "migrations"


def _migration_files() -> list[Path]:
    """Return migration files in numeric order (001_, 002_, …)."""
    return sorted(_MIGRATIONS_DIR.glob("*.sql"))


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        log.error("DATABASE_URL not set")
        return 1

    files = _migration_files()
    if not files:
        log.error("no migrations found", dir=str(_MIGRATIONS_DIR))
        return 1

    log.info("applying_migrations", count=len(files))

    # psycopg connection strings use `postgresql://` not `postgresql+psycopg://`
    # (the latter is SQLAlchemy's dialect name). Strip the `+psycopg` if present.
    if db_url.startswith("postgresql+psycopg://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg://"):]

    with psycopg.connect(db_url, autocommit=False) as conn:
        for f in files:
            sql = f.read_text()
            log.info("migrate", file=f.name, bytes=len(sql))
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    log.info("applying_migrations.done", count=len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
