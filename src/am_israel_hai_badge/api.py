from __future__ import annotations

import json
import logging
import time
import urllib.request
from datetime import date

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
