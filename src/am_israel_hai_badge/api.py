from __future__ import annotations

import json
import logging
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_BASE_URL = "https://oref-map.org"
_TIMEOUT = 30
_MAX_RETRIES = 3
_BACKOFF_BASE = 1  # seconds
_REQUEST_DELAY = 0.5  # seconds between requests


def _fetch_json(url: str) -> list[dict] | dict | None:
    """Fetch JSON from URL with retries and exponential backoff."""
    for attempt in range(_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "am-israel-hai-badge/0.1"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except Exception as exc:
            wait = _BACKOFF_BASE * (2 ** attempt)
            logger.warning("Fetch %s attempt %d failed: %s — retrying in %ds", url, attempt + 1, exc, wait)
            time.sleep(wait)
    logger.error("Failed to fetch %s after %d attempts", url, _MAX_RETRIES)
    return None


def fetch_day_history(day: date) -> list[dict]:
    """Fetch full-day archive for a specific date."""
    url = f"{_BASE_URL}/api/day-history?date={day.isoformat()}"
    result = _fetch_json(url)
    time.sleep(_REQUEST_DELAY)
    if isinstance(result, list):
        return result
    return []


def fetch_history() -> list[dict]:
    """Fetch recent alerts (last ~1-2 hours)."""
    url = f"{_BASE_URL}/api/history"
    result = _fetch_json(url)
    time.sleep(_REQUEST_DELAY)
    if isinstance(result, list):
        return result
    return []


def fetch_github_commit_count(username: str, days: int = 30) -> int:
    """Count push-event commits for a GitHub user in the last N days.

    Uses the public Events API (no auth needed, up to 10 pages / 300 events).
    """
    if not username:
        return 0

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    total = 0

    for page in range(1, 11):  # max 10 pages
        url = f"https://api.github.com/users/{username}/events/public?per_page=30&page={page}"
        data = _fetch_json(url)
        if not data or not isinstance(data, list):
            break

        page_has_old = False
        for event in data:
            created = event.get("created_at", "")
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            if ts < cutoff:
                page_has_old = True
                break

            if event.get("type") == "PushEvent":
                payload = event.get("payload", {})
                commits = payload.get("commits", [])
                # Some events include commit list, others just before/head
                total += len(commits) if commits else 1

        if page_has_old or len(data) < 30:
            break

    return total
