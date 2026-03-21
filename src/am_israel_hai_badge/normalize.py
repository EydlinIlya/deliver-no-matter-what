from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .models import Alert, SignalType

_TZ = ZoneInfo("Asia/Jerusalem")

# --- history API (numeric category) ---
_HISTORY_PREPARATORY = 14
_HISTORY_SAFETY = 13
# categories 1-12 are active alerts

# --- day-history API (string category_desc) ---
_DAY_PREPARATORY_DESC = "בדקות הקרובות צפויות להתקבל התרעות באזורך"
_DAY_SAFETY_DESC = "האירוע הסתיים"


def _parse_timestamp(raw: str) -> datetime:
    """Parse timestamp from either API format, localized to Asia/Jerusalem."""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            naive = datetime.strptime(raw, fmt)
            return naive.replace(tzinfo=_TZ)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: {raw!r}")


def _signal_from_category(cat: int) -> SignalType:
    if cat == _HISTORY_PREPARATORY:
        return SignalType.PREPARATORY
    if cat == _HISTORY_SAFETY:
        return SignalType.SAFETY
    if 1 <= cat <= 12:
        return SignalType.ACTIVE_ALERT
    raise ValueError(f"Unknown category: {cat}")


def _signal_from_desc(desc: str) -> SignalType:
    if desc == _DAY_PREPARATORY_DESC:
        return SignalType.PREPARATORY
    if desc == _DAY_SAFETY_DESC:
        return SignalType.SAFETY
    return SignalType.ACTIVE_ALERT


def normalize_history_alert(raw: dict) -> list[Alert]:
    """Normalize a single record from /api/history into Alert(s).

    The `data` field is a comma-separated string of area names.
    Each area produces one Alert.
    """
    ts = _parse_timestamp(raw["alertDate"])
    signal = _signal_from_category(int(raw["category"]))
    title = raw.get("title", "")
    areas = [a.strip() for a in raw.get("data", "").split(",") if a.strip()]
    return [Alert(timestamp=ts, area=area, signal_type=signal, title=title) for area in areas]


def normalize_day_history_alert(raw: dict) -> list[Alert]:
    """Normalize a single record from /api/day-history into Alert(s).

    The `data` field is a comma-separated string of area names.
    """
    ts = _parse_timestamp(raw["alertDate"])
    signal = _signal_from_desc(raw.get("category_desc", ""))
    title = raw.get("title", "")
    areas = [a.strip() for a in raw.get("data", "").split(",") if a.strip()]
    return [Alert(timestamp=ts, area=area, signal_type=signal, title=title) for area in areas]
