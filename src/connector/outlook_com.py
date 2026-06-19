"""Reads ONE shared team calendar from the desktop Outlook app via COM.

Requires: Windows, Outlook installed & signed in, pywin32, and the shared
calendar already added to your Outlook profile.

Outlook constants used:
  olFolderCalendar = 9        (default Calendar folder of a resolved recipient)
  olAppointmentItem item class
  BusyStatus: 0 Free, 1 Tentative, 2 Busy, 3 OutOfOffice, 4 WorkingElsewhere
"""
from __future__ import annotations

from datetime import datetime

try:
    import win32com.client  # type: ignore
    import pywintypes        # type: ignore
except ImportError:  # keeps the module importable on non-Windows for tests
    win32com = None
    pywintypes = None

from ..models import RawEvent
from .base import CalendarConnector

OL_FOLDER_CALENDAR = 9


class OutlookComConnector(CalendarConnector):
    def __init__(self, cfg: dict):
        if win32com is None:
            raise RuntimeError(
                "pywin32 is not available. Install requirements and run on "
                "Windows with Outlook installed."
            )
        self.cfg = cfg or {}
        self.method = self.cfg.get("method", "shared_mailbox")
        self.owner = self.cfg.get("owner", "")
        self.folder_name = self.cfg.get("folder_name", "")

    # ── public API ────────────────────────────────────────────────────────
    def get_events(self, start: datetime, end: datetime) -> list[RawEvent]:
        app = win32com.client.Dispatch("Outlook.Application")
        ns = app.GetNamespace("MAPI")
        folder = self._open_calendar(ns)
        items = self._restrict_to_range(folder, start, end)
        return [self._to_raw_event(it) for it in items]

    # ── calendar resolution ───────────────────────────────────────────────
    def _open_calendar(self, ns):
        if self.method == "shared_mailbox":
            if not self.owner:
                raise ValueError("config calendar.owner is required for shared_mailbox")
            recipient = ns.CreateRecipient(self.owner)
            recipient.Resolve()
            if not recipient.Resolved:
                raise RuntimeError(
                    f"Could not resolve shared mailbox owner: {self.owner!r}. "
                    "Check the name/SMTP and that it is shared to you."
                )
            return ns.GetSharedDefaultFolder(recipient, OL_FOLDER_CALENDAR)

        if self.method == "named_folder":
            folder = self._find_folder_by_name(ns, self.folder_name)
            if folder is None:
                raise RuntimeError(
                    f"Could not find a calendar folder named {self.folder_name!r}. "
                    "Add it under 'Other Calendars' in Outlook first."
                )
            return folder

        raise ValueError(f"Unknown calendar.method: {self.method!r}")

    def _find_folder_by_name(self, ns, name: str):
        """Depth-first search across all stores for a folder by display name."""
        target = (name or "").strip().lower()
        for store in ns.Folders:
            found = self._search_folder(store, target)
            if found is not None:
                return found
        return None

    def _search_folder(self, folder, target: str):
        try:
            if folder.Name.strip().lower() == target:
                return folder
        except Exception:
            pass
        try:
            subfolders = folder.Folders
        except Exception:
            return None
        for sub in subfolders:
            found = self._search_folder(sub, target)
            if found is not None:
                return found
        return None

    # ── querying ──────────────────────────────────────────────────────────
    def _restrict_to_range(self, folder, start: datetime, end: datetime):
        """Use Items.Restrict for a fast server-side date filter.

        IncludeRecurrences must be set BEFORE sorting/restricting so recurring
        PTO (e.g. recurring half-day) is expanded into individual occurrences.
        """
        items = folder.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")
        # Outlook expects US-style date strings in Restrict filters.
        fmt = "%m/%d/%Y %I:%M %p"
        restriction = (
            f"[Start] <= '{end.strftime(fmt)}' AND "
            f"[End] >= '{start.strftime(fmt)}'"
        )
        return items.Restrict(restriction)

    # ── mapping ───────────────────────────────────────────────────────────
    def _to_raw_event(self, item) -> RawEvent:
        organizer = ""
        try:
            organizer = item.Organizer or ""
        except Exception:
            pass

        categories: list[str] = []
        try:
            if item.Categories:
                categories = [c.strip() for c in item.Categories.split(",") if c.strip()]
        except Exception:
            pass

        busy = None
        try:
            busy = int(item.BusyStatus)
        except Exception:
            pass

        return RawEvent(
            subject=getattr(item, "Subject", "") or "",
            start=self._to_dt(item.Start),
            end=self._to_dt(item.End),
            all_day=bool(getattr(item, "AllDayEvent", False)),
            organizer=organizer,
            categories=categories,
            busy_status=busy,
            body=(getattr(item, "Body", "") or "")[:500],
        )

    @staticmethod
    def _to_dt(value) -> datetime:
        # pywintypes.datetime -> aware; normalize to naive local for simplicity.
        dt = datetime.fromtimestamp(value.timestamp()) if hasattr(value, "timestamp") else value
        return dt.replace(tzinfo=None)
