"""Repository for data quality / reconciliation stats."""

from dataclasses import dataclass

import psycopg


@dataclass
class TrustStats:
    origence_row_count: int
    symitar_row_count: int
    reconciliation_match_rate: float


def get_trust_stats(db_url: str) -> TrustStats:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applications")
        origence_count: int = (cur.fetchone() or (0,))[0]
        cur.execute("SELECT COUNT(*) FROM booked_loans")
        symitar_count: int = (cur.fetchone() or (0,))[0]
        cur.execute("SELECT COUNT(*) FROM reconciliation_bridge")
        total: int = (cur.fetchone() or (0,))[0]
        cur.execute(
            "SELECT COUNT(*) FROM reconciliation_bridge"
            " WHERE match_type = 'matched'"
        )
        matched: int = (cur.fetchone() or (0,))[0]
    rate = matched / total if total > 0 else 0.0
    return TrustStats(
        origence_row_count=origence_count,
        symitar_row_count=symitar_count,
        reconciliation_match_rate=rate,
    )
