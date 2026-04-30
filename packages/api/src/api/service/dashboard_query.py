"""Dashboard service: MTD/YTD date helpers and in-process TTL cache."""

import time
from datetime import date

_TTL = 300.0
_cache: dict[tuple[str, str], tuple[float, object]] = {}


def _monotonic() -> float:
    return time.monotonic()


# ── Date helpers ──────────────────────────────────────────────────────────────


def mtd_range(as_of: date) -> tuple[date, date]:
    """Return (first of month, as_of)."""
    return date(as_of.year, as_of.month, 1), as_of


def ytd_range(as_of: date) -> tuple[date, date]:
    """Return (Jan 1 of current year, as_of)."""
    return date(as_of.year, 1, 1), as_of


def prior_ytd_range(as_of: date) -> tuple[date, date]:
    """Return same day-of-year window one year earlier."""
    return date(as_of.year - 1, 1, 1), date(as_of.year - 1, as_of.month, as_of.day)


# ── In-process TTL cache ──────────────────────────────────────────────────────


def cache_get(endpoint: str, as_of_date: str) -> object | None:
    """Return cached value for (endpoint, as_of_date) or None if absent/expired."""
    entry = _cache.get((endpoint, as_of_date))
    if entry is None:
        return None
    expires_at, value = entry
    if _monotonic() > expires_at:
        del _cache[(endpoint, as_of_date)]
        return None
    return value


def cache_set(endpoint: str, as_of_date: str, value: object) -> None:
    """Store value in cache with a _TTL-second expiry."""
    _cache[(endpoint, as_of_date)] = (_monotonic() + _TTL, value)


def cache_clear() -> None:
    """Evict all entries — used in tests."""
    _cache.clear()
