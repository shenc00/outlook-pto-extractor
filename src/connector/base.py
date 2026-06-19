"""Connector interface — the swappable seam.

Any backend (Outlook COM today, Microsoft Graph later) implements this so the
parser and Excel layers never depend on a specific provider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import RawEvent


class CalendarConnector(ABC):
    @abstractmethod
    def get_events(self, start: datetime, end: datetime) -> list[RawEvent]:
        """Return all appointments on the shared team calendar that overlap
        the [start, end] window, as provider-agnostic RawEvent records."""
        raise NotImplementedError
