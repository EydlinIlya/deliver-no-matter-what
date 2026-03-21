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
    """Count commits for a GitHub user in the last N days.

    Uses GitHub GraphQL API with contributionsCollection.
    Includes both public and private repo commits.
    Requires GITHUB_TOKEN env var or gh CLI auth.
    """
    if not username:
        return 0

    import os
    import subprocess

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        try:
            token = subprocess.check_output(
                ["gh", "auth", "token"], stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            logger.warning("No GitHub token available, skipping commit count")
            return 0

    now = datetime.now(tz=timezone.utc)
    from_date = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    query = json.dumps({"query": (
        '{ user(login: "' + username + '") {'
        '  contributionsCollection(from: "' + from_date + '", to: "' + to_date + '") {'
        "    totalCommitContributions"
        "    restrictedContributionsCount"
        "  }"
        "} }"
    )}).encode()

    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=query,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "am-israel-hai-badge/0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        cc = data["data"]["user"]["contributionsCollection"]
        return cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    except Exception as exc:
        logger.warning("GitHub GraphQL query failed: %s", exc)
        return 0
