from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class SignalType(enum.Enum):
    PREPARATORY = "preparatory"
    ACTIVE_ALERT = "active_alert"
    SAFETY = "safety"


@dataclass(frozen=True)
class Alert:
    timestamp: datetime
    area: str
    signal_type: SignalType
    title: str


@dataclass
class ShelterSession:
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_signal: SignalType
    area: str

    @property
    def duration_seconds(self) -> float:
        if self.exit_time is None:
            return 0.0
        return (self.exit_time - self.entry_time).total_seconds()
