from __future__ import annotations

from pathlib import Path

from .time_fmt import format_duration

_BADGE_DIR = Path(__file__).resolve().parents[2] / "badges"

_SVG_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg" width="380" height="80" viewBox="0 0 380 80">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2d333b"/>
      <stop offset="100%" stop-color="#22272e"/>
    </linearGradient>
  </defs>
  <rect width="380" height="80" rx="8" fill="url(#bg)" stroke="#444c56" stroke-width="1"/>
  <text x="22" y="28" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="14" font-weight="600" fill="#e6edf3">
    {shield} Time in Shelter
  </text>
  <line x1="16" y1="40" x2="364" y2="40" stroke="#444c56" stroke-width="1"/>
  <text x="22" y="62" font-family="Segoe UI Mono,SF Mono,Menlo,monospace" font-size="13" fill="#9198a1">
    <tspan fill="#e6edf3" font-weight="600">24h</tspan> {h24}
    <tspan dx="16" fill="#e6edf3" font-weight="600">7d</tspan> {d7}
    <tspan dx="16" fill="#e6edf3" font-weight="600">30d</tspan> {d30}
  </text>
</svg>"""


def generate_badge(seconds_24h: float, seconds_7d: float, seconds_30d: float) -> str:
    """Generate SVG badge content."""
    return _SVG_TEMPLATE.format(
        shield="\U0001f6e1\ufe0f",  # 🛡️
        h24=format_duration(seconds_24h),
        d7=format_duration(seconds_7d),
        d30=format_duration(seconds_30d),
    )


def write_badge(seconds_24h: float, seconds_7d: float, seconds_30d: float) -> Path:
    """Generate and write SVG badge to badges/shelter.svg."""
    _BADGE_DIR.mkdir(parents=True, exist_ok=True)
    path = _BADGE_DIR / "shelter.svg"
    svg = generate_badge(seconds_24h, seconds_7d, seconds_30d)
    path.write_text(svg, encoding="utf-8")
    return path
