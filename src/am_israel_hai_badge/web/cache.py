"""Thread-safe in-memory cache of alert data and computed shelter sessions."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..normalize import normalize_alert
from ..shelter import compute_sessions, shelter_seconds_in_window

logger = logging.getLogger(__name__)
_TZ = ZoneInfo("Asia/Jerusalem")


class AlertCache:
    """Holds all alert records in memory with lazy per-area session computation.

    The background worker calls ``refresh()`` every 15 minutes with all
    records from the CSV cache.  Badge endpoints call ``get_badge_data()``
    which filters to the requested areas and caches the session list.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._all_records: list[dict] = []
        self._sessions_cache: dict[frozenset[str], list] = {}
        self._last_refresh: datetime | None = None

    @property
    def last_refresh(self) -> datetime | None:
        return self._last_refresh

    @property
    def record_count(self) -> int:
        return len(self._all_records)

    def refresh(self, records: list[dict]) -> None:
        """Replace all records and clear the per-area session cache."""
        with self._lock:
            self._all_records = records
            self._sessions_cache.clear()
            self._last_refresh = datetime.now(tz=_TZ)
        logger.info("AlertCache refreshed: %d records", len(records))

    def get_badge_data(
        self, area_names: list[str],
    ) -> tuple[float, float, float]:
        """Return (seconds_24h, seconds_7d, seconds_30d) for the given areas."""
        area_key = frozenset(area_names)
        now = datetime.now(tz=_TZ)

        with self._lock:
            if area_key not in self._sessions_cache:
                # Filter records to these areas, then normalize + compute
                area_set = set(area_names)
                filtered: list[dict] = []
                for rec in self._all_records:
                    city = rec.get("data", "")
                    cat = rec.get("category", 0)
                    if city == "*":
                        # Only expand broadcast SAFETY signals
                        if cat != 13:
                            continue
                        for area in area_names:
                            filtered.append({**rec, "data": area})
                    elif city in area_set:
                        filtered.append(rec)

                alerts = []
                for rec in filtered:
                    try:
                        alerts.extend(normalize_alert(rec))
                    except Exception:
                        pass
                self._sessions_cache[area_key] = compute_sessions(
                    alerts, area_names,
                )

            sessions = self._sessions_cache[area_key]

        s_24h = shelter_seconds_in_window(
            sessions, now - timedelta(hours=24), now,
        )
        s_7d = shelter_seconds_in_window(
            sessions, now - timedelta(days=7), now,
        )
        s_30d = shelter_seconds_in_window(
            sessions, now - timedelta(days=30), now,
        )
        return s_24h, s_7d, s_30d
