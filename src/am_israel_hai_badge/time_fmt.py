from __future__ import annotations


def format_duration(total_seconds: int | float) -> str:
    """Format seconds into a human-readable duration string like '2h 15m'."""
    total_seconds = max(0, int(total_seconds))
    if total_seconds == 0:
        return "0m"

    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60

    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"
