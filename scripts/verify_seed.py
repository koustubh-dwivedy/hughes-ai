"""HUG-253: assert seed row counts match the small_cu profile.

Called at the end of infra/bootstrap.sh. Exits non-zero if any count is
below the expected floor.
"""

from __future__ import annotations

import os
import sys

import psycopg
import structlog

log = structlog.get_logger()

# Floors from packages/synth-data/profiles/small_cu.yaml. Use floors rather
# than equality because dbt-build may add rows to materialized marts and we
# only want to detect "seed didn't run" or "schema reset wiped data".
_FLOORS = {
    "members": 3000,
    "deposit_accounts": 8000,
    "applications": 500,
}


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        log.error("DATABASE_URL not set")
        return 1

    if db_url.startswith("postgresql+psycopg://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg://"):]

    failures: list[str] = []
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        for table, floor in _FLOORS.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608  # nosec B608
            row = cur.fetchone()
            count = row[0] if row else 0
            status = "ok" if count >= floor else "below_floor"
            log.info("seed_count", table=table, count=count, floor=floor, status=status)
            if count < floor:
                failures.append(f"{table}: {count} < floor {floor}")

    if failures:
        log.error("seed_verification.failed", failures=failures)
        return 1

    log.info("seed_verification.ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
