"""Standalone script for GitHub Actions: fetch alerts, compute shelter times, update badge data.

Reuses existing code — no new logic. Connects to Supabase PostgreSQL via DATABASE_URL.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_WAR_FROM = "2026-02-26T00:00:00Z"
_WAR_TO   = "2026-04-16T23:59:59Z"

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
        _fetch_cities_data,
        fetch_github_commit_count,
        read_all_cached_records,
        update_csv_cache,
    )
    from .cache import AlertCache
    from .db import Database

    db = Database(database_url)

    # 1. Restore CSVs from DB (incremental sync — pick up where we left off)
    _CSV_NAMES = ("tzevaadom_alerts.csv", "tzevaadom_messages.csv")
    restored = False
    for name in _CSV_NAMES:
        path = _DATA_DIR / name
        if path.exists() and path.stat().st_size > 0:
            continue
        content = db.load_csv(name)
        if content:
            path.write_text(content, encoding="utf-8")
            restored = True
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

    # 4. Load all records and build cache
    records = read_all_cached_records()
    logger.info("Total records: %d", len(records))

    cache = AlertCache()
    cache.refresh(records)

    # 5. Compute shelter times for ALL areas → area_times table
    try:
        cities = _fetch_cities_data()
        all_area_names = [name for name, info in cities.items() if isinstance(info, dict)]
        logger.info("Computing shelter times for %d areas...", len(all_area_names))

        area_rows: list[tuple[str, float, float, float, float]] = []
        for area_name in all_area_names:
            s_24h, s_7d, s_30d = cache.get_badge_data(area_name)
            s_war = cache.get_war_shelter_time(area_name)
            area_rows.append((area_name, s_24h, s_7d, s_30d, s_war))

        db.save_area_times_batch(area_rows)
        nonzero = sum(1 for _, s24, s7, s30, sw in area_rows if s24 or s7 or s30 or sw)
        logger.info("Saved area_times: %d areas (%d with activity)", len(area_rows), nonzero)
    except Exception:
        logger.exception("Failed to compute area_times")

    # 6. Update per-badge contribution counts (using bot PAT, not per-user tokens)
    gh_pat = os.environ.get("GH_PAT", "")
    badges = db._fetchall("SELECT token, github_login FROM badges")
    logger.info("Updating contributions for %d badges", len(badges))

    for badge in badges:
        token = badge["token"]
        commits = 0
        gh_login = badge.get("github_login", "")
        if gh_login and gh_pat:
            try:
                commits = fetch_github_commit_count(gh_login, token=gh_pat)
            except Exception:
                pass

        war_commits = 0
        if gh_login and gh_pat:
            try:
                war_commits = fetch_github_commit_count(gh_login, token=gh_pat,
                                                        from_dt=_WAR_FROM, to_dt=_WAR_TO)
            except Exception:
                pass

        db.save_badge_data(token, commits, war_commits)
        logger.info("  %s: commits=%d war_commits=%d", token, commits, war_commits)

    db.close()
    logger.info("Done.")


if __name__ == "__main__":
    main()
