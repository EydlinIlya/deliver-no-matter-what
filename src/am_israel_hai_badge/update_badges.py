"""Standalone script for GitHub Actions: fetch alerts, compute shelter times, update badge data.

Reuses existing code — no new logic. Connects to Supabase PostgreSQL via DATABASE_URL.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
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
    from .cache import _WAR_END, _WAR_START, AlertCache
    from .db import Database

    # Marker stored in csv_cache once the (now-finished) war window has been
    # computed in full, so we never recompute the static s_war again.
    _WAR_DONE_MARKER = "war_s_war_computed_v1"

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

    # 4. Load records for the rolling badge windows (24h/7d/30d).
    records = read_all_cached_records()
    logger.info("Total records: %d", len(records))

    cache = AlertCache()
    cache.refresh(records)

    # 5. Compute shelter times for ALL areas → area_times table
    try:
        cities = _fetch_cities_data()
        all_area_names = [name for name, info in cities.items() if isinstance(info, dict)]
        logger.info("Computing shelter times for %d areas...", len(all_area_names))

        # 5a. Rolling windows — recomputed every run.
        rolling_rows: list[tuple[str, float, float, float]] = []
        for area_name in all_area_names:
            s_24h, s_7d, s_30d = cache.get_badge_data(area_name)
            rolling_rows.append((area_name, s_24h, s_7d, s_30d))
        db.save_area_rolling_times_batch(rolling_rows)
        nonzero = sum(1 for _, s24, s7, s30 in rolling_rows if s24 or s7 or s30)
        logger.info("Saved rolling area_times: %d areas (%d with activity)",
                    len(rolling_rows), nonzero)

        # 5b. War window (Lion's Roar) — fixed [Feb 26, Apr 16]. Compute once,
        # then mark done and skip forever (the data is static now).
        now = datetime.now(tz=_WAR_END.tzinfo)
        if now > _WAR_END and db.load_csv(_WAR_DONE_MARKER):
            logger.info("s_war already finalized — skipping war recompute")
        else:
            war_records = read_all_cached_records(since=_WAR_START, until=_WAR_END)
            logger.info("War-window records: %d", len(war_records))
            war_cache = AlertCache()
            war_cache.refresh(war_records)
            war_rows = [(a, war_cache.get_war_shelter_time(a)) for a in all_area_names]
            db.save_area_war_times_batch(war_rows)
            if now > _WAR_END:
                db.save_csv(_WAR_DONE_MARKER, now.isoformat())
            logger.info("Saved s_war for %d areas%s", len(war_rows),
                        " (finalized)" if now > _WAR_END else "")
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
