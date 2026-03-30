"""Background thread that periodically refreshes the alert CSV cache."""
from __future__ import annotations

import logging
import os
import threading
import urllib.request
from pathlib import Path

from ..api import read_all_cached_records, update_csv_cache
from .cache import AlertCache

logger = logging.getLogger(__name__)

REFRESH_INTERVAL = 15 * 60  # 15 minutes
KEEPALIVE_INTERVAL = 5 * 60  # 5 minutes — prevent Render free-tier sleep

_CSV_NAMES = ("tzevaadom_alerts.csv", "tzevaadom_messages.csv")


def _keepalive_loop(stop: threading.Event) -> None:
    """Ping own /health endpoint to prevent Render from sleeping the service."""
    base = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not base:
        logger.info("RENDER_EXTERNAL_URL not set — keepalive disabled")
        return
    url = f"{base}/health"
    while not stop.is_set():
        stop.wait(KEEPALIVE_INTERVAL)
        if stop.is_set():
            break
        try:
            urllib.request.urlopen(url, timeout=10)
        except Exception:
            logger.debug("Keepalive ping failed (non-critical)")


def restore_csvs_from_db(db, data_dir: Path) -> bool:
    """Restore CSV files from the database on cold start.

    Returns True if any CSV was restored.
    """
    restored = False
    for name in _CSV_NAMES:
        path = data_dir / name
        if path.exists() and path.stat().st_size > 0:
            continue  # already have local data
        content = db.load_csv(name)
        if content:
            path.write_text(content, encoding="utf-8")
            logger.info("Restored %s from database (%d bytes)", name, len(content))
            restored = True
    return restored


def _save_csvs_to_db(db, data_dir: Path) -> None:
    """Persist CSV files to the database after a refresh."""
    for name in _CSV_NAMES:
        path = data_dir / name
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                if content:
                    db.save_csv(name, content)
            except Exception:
                logger.debug("Failed to persist %s to database", name)


def _refresh_loop(
    cache: AlertCache, db, data_dir: Path,
    stop: threading.Event, interval: int,
) -> None:
    """Fetch new alerts from the API and refresh the in-memory cache."""
    while not stop.is_set():
        try:
            update_csv_cache()
            records = read_all_cached_records()
            cache.refresh(records)
            _save_csvs_to_db(db, data_dir)
        except Exception:
            logger.exception("Cache refresh failed")
        stop.wait(interval)


def start_worker(
    cache: AlertCache, db=None, data_dir: Path | None = None,
    interval: int = REFRESH_INTERVAL,
) -> tuple[threading.Thread, threading.Event]:
    """Start the background refresh thread. Returns (thread, stop_event)."""
    stop = threading.Event()
    thread = threading.Thread(
        target=_refresh_loop,
        args=(cache, db, data_dir, stop, interval),
        daemon=True,
        name="alert-worker",
    )
    thread.start()
    logger.info("Background worker started (interval=%ds)", interval)

    # Keepalive thread to prevent Render free-tier from sleeping
    ka_thread = threading.Thread(
        target=_keepalive_loop,
        args=(stop,),
        daemon=True,
        name="keepalive",
    )
    ka_thread.start()

    return thread, stop
