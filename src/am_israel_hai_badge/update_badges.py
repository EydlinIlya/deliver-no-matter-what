"""Standalone script for GitHub Actions: fetch alerts, compute shelter times, update badge data.

Reuses existing code — no new logic. Connects to Supabase PostgreSQL via DATABASE_URL.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# DATA_DIR for CSV temp storage (ephemeral in GH Actions runner)
_DATA_DIR = Path(os.environ.get("DATA_DIR", "/tmp/shelter-data"))


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Set DATA_DIR so api.py uses our temp dir
    os.environ["DATA_DIR"] = str(_DATA_DIR)

    from .api import (
        fetch_github_commit_count,
        read_all_cached_records,
        update_csv_cache,
    )
    from .web.cache import AlertCache
    from .web.db import Database
    from .web.worker import restore_csvs_from_db

    db = Database(database_url)

    # 1. Restore CSVs from DB (incremental sync — pick up where we left off)
    restored = restore_csvs_from_db(db, _DATA_DIR)
    logger.info("CSV restore: %s", "restored from DB" if restored else "no prior data")

    # 2. Fetch new alerts from tzevaadom API (incremental)
    logger.info("Fetching new alerts...")
    update_csv_cache()

    # 3. Save updated CSVs back to DB
    for name in ("tzevaadom_alerts.csv", "tzevaadom_messages.csv"):
        path = _DATA_DIR / name
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if content:
                db.save_csv(name, content)
                logger.info("Saved %s to DB (%d bytes)", name, len(content))

    # 4. Compute shelter times for all badges
    records = read_all_cached_records()
    logger.info("Total records: %d", len(records))

    cache = AlertCache()
    cache.refresh(records)

    badges = db._fetchall("SELECT token, area_names, github_login, github_token FROM badges")
    logger.info("Processing %d badges", len(badges))

    for badge in badges:
        token = badge["token"]
        area_raw = json.loads(badge["area_names"])
        area_name = area_raw[0] if isinstance(area_raw, list) else area_raw

        s_24h, s_7d, s_30d = cache.get_badge_data(area_name)

        commits = 0
        gh_login = badge.get("github_login", "")
        gh_token = badge.get("github_token", "")
        if gh_login and gh_token:
            try:
                commits = fetch_github_commit_count(gh_login, token=gh_token)
            except Exception:
                pass

        db.save_badge_data(token, s_24h, s_7d, s_30d, commits)
        logger.info(
            "  %s (%s): 24h=%dm 7d=%.1fh 30d=%.1fh commits=%d",
            token, area_name, s_24h / 60, s_7d / 3600, s_30d / 3600, commits,
        )

    db.close()
    logger.info("Done.")


if __name__ == "__main__":
    main()
