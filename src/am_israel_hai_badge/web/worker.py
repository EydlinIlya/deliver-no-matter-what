"""Background thread that periodically refreshes the alert CSV cache."""
from __future__ import annotations

import logging
import threading

from ..api import read_all_cached_records, update_csv_cache
from .cache import AlertCache

logger = logging.getLogger(__name__)

REFRESH_INTERVAL = 15 * 60  # 15 minutes


def _refresh_loop(
    cache: AlertCache, stop: threading.Event, interval: int,
) -> None:
    """Fetch new alerts from the API and refresh the in-memory cache."""
    while not stop.is_set():
        try:
            update_csv_cache()
            records = read_all_cached_records()
            cache.refresh(records)
        except Exception:
            logger.exception("Cache refresh failed")
        stop.wait(interval)


def start_worker(
    cache: AlertCache, interval: int = REFRESH_INTERVAL,
) -> tuple[threading.Thread, threading.Event]:
    """Start the background refresh thread. Returns (thread, stop_event)."""
    stop = threading.Event()
    thread = threading.Thread(
        target=_refresh_loop,
        args=(cache, stop, interval),
        daemon=True,
        name="alert-worker",
    )
    thread.start()
    logger.info("Background worker started (interval=%ds)", interval)
    return thread, stop
