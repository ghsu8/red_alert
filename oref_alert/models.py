"""Domain models used by the Red Alert notifier."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class AlertType(str, Enum):
    MISSILE = "T"
    AIRCRAFT = "A"
    EARLY_WARNING = "EW"
    ALL = "ALL"


@dataclass
class AlertEvent:
    id: str
    type: AlertType
    headline: str
    timestamp: str
    cities: List[str]
    raw: dict


@dataclass
class PointOfInterest:
    city: str
    latitude: float
    longitude: float


@dataclass
class AlertSummary:
    """Represents a processed alert ready for display."""

    id: str
    type: AlertType
    title: str
    cities: List[str]
    details: Optional[str] = None
    color: str = "#F87171"  # default to red

    def is_missile(self) -> bool:
        return self.type == AlertType.MISSILE

    def is_aircraft(self) -> bool:
        return self.type == AlertType.AIRCRAFT
