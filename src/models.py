"""Shared data structures passed between layers.

RawEvent  : a calendar appointment as read by a connector (provider-agnostic).
PtoEntry  : a normalized PTO record after parsing (person + day count).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class RawEvent:
    """A calendar appointment, normalized across connectors (COM / Graph)."""
    subject: str
    start: datetime
    end: datetime
    all_day: bool
    organizer: str = ""
    categories: list[str] = field(default_factory=list)
    busy_status: int | None = None  # Outlook: 0 Free, 1 Tentative, 2 Busy, 3 OOF
    body: str = ""

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass
class PtoEntry:
    """One person's time off over a contiguous span."""
    person: str
    start: datetime
    end: datetime
    days: float                              # business days in range (half-days allowed)
    dates: list[date] = field(default_factory=list)  # the business days occupied
    tentative: bool = False                  # busy status was Tentative
    pto_type: str = "PTO"
    note: str = ""
    source_subject: str = ""
