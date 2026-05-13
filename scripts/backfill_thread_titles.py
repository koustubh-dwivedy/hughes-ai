"""One-off backfill: stamp LLM-generated titles on threads that were
created before the auto-title rollout.

Walks `threads` where `title IS NULL`, fetches the first user message
from `thread_messages`, asks the LLM (same Ollama GLM-5.1 the agent
uses) for a 3-6 word sidebar title, and writes it via
`update_thread_title` (which is conditional on `title IS NULL` so the
script is safe to re-run).

Run with:
    DATABASE_URL=postgresql://... uv run python scripts/backfill_thread_titles.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

# Reach into packages/api/src and packages/nl-engine/src without installing.
sys.path.insert(0, str(REPO_ROOT / "packages" / "api" / "src"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "nl-engine" / "src"))

from api.repo import threads as threads_repo  # noqa: E402
from api.services.title_generator import generate_title  # noqa: E402
from nl_engine.llm import make_llm  # noqa: E402


def _null_title_thread_ids(db_url: str) -> list[str]:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT thread_id FROM threads WHERE title IS NULL"
            " ORDER BY started_at ASC"
        )
        return [row[0] for row in cur.fetchall()]


def _first_user_message(thread_id: str, db_url: str) -> str | None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT content FROM thread_messages"
            " WHERE thread_id = %s AND role = 'user'"
            " ORDER BY created_at ASC LIMIT 1",
            (thread_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated, but don't write.",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    thread_ids = _null_title_thread_ids(db_url)
    if not thread_ids:
        print("No threads with NULL title. Nothing to do.")
        return 0

    print(f"Found {len(thread_ids)} thread(s) without a title.")
    llm = make_llm() if not args.dry_run else None
    written = 0
    skipped_no_message = 0
    for tid in thread_ids:
        first = _first_user_message(tid, db_url)
        if not first:
            skipped_no_message += 1
            continue
        if args.dry_run:
            title = first.split("\n")[0][:60]
            print(f"  [dry-run] {tid} → {title!r}")
            continue
        if llm is None:  # pragma: no cover — narrowing only
            raise RuntimeError("LLM was not constructed; expected dry_run only")
        title = generate_title(first, llm)
        wrote = threads_repo.update_thread_title(tid, title, db_url)
        flag = "✓" if wrote else "skip"
        print(f"  [{flag}] {tid} → {title!r}")
        if wrote:
            written += 1

    print()
    print(f"Updated {written} thread(s).")
    if skipped_no_message:
        print(f"Skipped {skipped_no_message} thread(s) with no user message.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
