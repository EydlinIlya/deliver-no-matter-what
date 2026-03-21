from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from .api import fetch_day_history, fetch_history
from .badge import write_badge
from .config import load_area_names
from .normalize import normalize_day_history_alert, normalize_history_alert
from .shelter import compute_sessions, total_shelter_seconds

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_CACHE_PATH = _DATA_DIR / "daily_totals.json"
_MAX_DAYS = 31


def _load_cache() -> dict[str, float | None]:
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict[str, float | None]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _prune_cache(cache: dict[str, float | None], today: date) -> dict[str, float | None]:
    cutoff = (today - timedelta(days=_MAX_DAYS)).isoformat()
    return {k: v for k, v in cache.items() if k >= cutoff}


def _compute_day_seconds(day: date, area_names: list[str]) -> float:
    """Fetch alerts for a single day and compute total shelter seconds."""
    today = date.today()
    alerts = []

    # Fetch day-history archive
    raw_records = fetch_day_history(day)
    for rec in raw_records:
        alerts.extend(normalize_day_history_alert(rec))

    # If today, also merge recent history endpoint for freshest data
    if day == today:
        raw_recent = fetch_history()
        for rec in raw_recent:
            alerts.extend(normalize_history_alert(rec))

    sessions = compute_sessions(alerts, area_names)
    return total_shelter_seconds(sessions)


def run() -> None:
    area_names = load_area_names()
    logger.info("Area names: %s", area_names)

    today = date.today()
    cache = _load_cache()

    # Determine which days need fetching
    days_to_fetch: list[date] = []
    for offset in range(30):
        day = today - timedelta(days=offset)
        day_str = day.isoformat()
        if day == today:
            # Always re-fetch today
            days_to_fetch.append(day)
        elif day_str not in cache or cache[day_str] is None:
            days_to_fetch.append(day)

    logger.info("Days to fetch: %d (of 30)", len(days_to_fetch))

    # Fetch and compute
    for day in days_to_fetch:
        day_str = day.isoformat()
        try:
            seconds = _compute_day_seconds(day, area_names)
            if day == today:
                cache[day_str] = None  # Mark today as incomplete (always re-fetch)
                cache[f"_today_seconds_{day_str}"] = seconds
            else:
                cache[day_str] = seconds
            logger.info("  %s: %.0f seconds", day_str, seconds)
        except Exception:
            logger.exception("  %s: failed to compute", day_str)

    # Prune old entries
    cache = _prune_cache(cache, today)

    _save_cache(cache)

    # Sum totals for each period
    today_str = today.isoformat()
    today_seconds = cache.get(f"_today_seconds_{today_str}", 0) or 0

    def sum_period(days: int) -> float:
        total = 0.0
        for offset in range(days):
            day = today - timedelta(days=offset)
            day_str = day.isoformat()
            if day == today:
                total += today_seconds
            elif day_str in cache and cache[day_str] is not None:
                total += cache[day_str]
        return total

    s_24h = sum_period(1)
    s_7d = sum_period(7)
    s_30d = sum_period(30)

    logger.info("Totals — 24h: %.0fs, 7d: %.0fs, 30d: %.0fs", s_24h, s_7d, s_30d)

    path = write_badge(s_24h, s_7d, s_30d)
    logger.info("Badge written to %s", path)


if __name__ == "__main__":
    run()
