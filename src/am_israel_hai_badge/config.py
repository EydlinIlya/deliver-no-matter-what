from __future__ import annotations

import os
import tomllib
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _PROJECT_ROOT / "config.toml"


def load_area_names() -> list[str]:
    """Load area names from BADGE_AREAS env var or config.toml."""
    env = os.environ.get("BADGE_AREAS", "").strip()
    if env:
        return [n.strip() for n in env.split(",") if n.strip()]

    with open(_CONFIG_PATH, "rb") as f:
        cfg = tomllib.load(f)
    return cfg["area"]["names"]
