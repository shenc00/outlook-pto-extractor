"""Turn RawEvents from the shared calendar into normalized PtoEntry records.

Two jobs, in order:
  1. Is this event PTO?      (categories / subject patterns / OOF busy status)
  2. Who is it for?          (subject regex -> organizer)  + roster canonicalize
Then count business days, honoring weekends, company holidays, and half-days.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from .models import PtoEntry, RawEvent

OL_OUT_OF_OFFICE = 3


class PtoParser:
    def __init__(self, cfg: dict):
        pto = cfg.get("pto", {})
        person = cfg.get("person", {})
        counting = cfg.get("counting", {})

        self.categories = {c.lower() for c in pto.get("categories", [])}
        self.subject_patterns = [
            re.compile(p, re.IGNORECASE) for p in pto.get("subject_patterns", [])
        ]
        self.match_oof = bool(pto.get("match_out_of_office", True))

        self.person_strategy = person.get("strategy", ["subject_regex", "organizer"])
        sr = person.get("subject_regex")
        self.subject_regex = re.compile(sr, re.IGNORECASE) if sr else None
        self.alias_map = self._build_alias_map(person.get("roster", {}) or {})
        self.roster_only = bool(self.alias_map)

        self.skip_weekends = bool(counting.get("skip_weekends", True))
        self.holidays = {self._as_date(d) for d in counting.get("company_holidays", [])}
        self.half_day_max_hours = float(counting.get("half_day_max_hours", 5))

    # ── orchestration ─────────────────────────────────────────────────────
    def parse(self, events: list[RawEvent]) -> tuple[list[PtoEntry], list[RawEvent]]:
        """Return (pto_entries, skipped_events). Skipped = not-PTO or no-person,
        surfaced so --dry-run can show what was dropped and why."""
        entries: list[PtoEntry] = []
        skipped: list[RawEvent] = []
        for ev in events:
            if not self._is_pto(ev):
                skipped.append(ev)
                continue
            person = self._extract_person(ev)
            if not person:
                skipped.append(ev)
                continue
            entries.append(
                PtoEntry(
                    person=person,
                    start=ev.start,
                    end=ev.end,
                    days=self._count_days(ev),
                    pto_type=self._classify_type(ev),
                    note=ev.subject,
                    source_subject=ev.subject,
                )
            )
        return entries, skipped

    # ── step 1: is it PTO? ────────────────────────────────────────────────
    def _is_pto(self, ev: RawEvent) -> bool:
        if self.categories and {c.lower() for c in ev.categories} & self.categories:
            return True
        if any(p.search(ev.subject) for p in self.subject_patterns):
            return True
        if self.match_oof and ev.busy_status == OL_OUT_OF_OFFICE:
            return True
        return False

    def _classify_type(self, ev: RawEvent) -> str:
        for cat in ev.categories:
            if cat.lower() in self.categories:
                return cat
        s = ev.subject.lower()
        for key in ("vacation", "holiday", "leave", "ooo", "pto"):
            if key in s:
                return key.upper() if len(key) <= 3 else key.capitalize()
        return "PTO"

    # ── step 2: who is it for? ────────────────────────────────────────────
    def _extract_person(self, ev: RawEvent) -> str | None:
        for strat in self.person_strategy:
            name = None
            if strat == "subject_regex" and self.subject_regex:
                m = self.subject_regex.search(ev.subject)
                if m and m.groupdict().get("name"):
                    name = m.group("name").strip()
            elif strat == "organizer" and ev.organizer:
                name = ev.organizer.strip()
            if name:
                canonical = self._canonicalize(name)
                if canonical:
                    return canonical
        return None

    def _canonicalize(self, name: str) -> str | None:
        if not self.alias_map:
            return name  # no roster -> keep whatever we found
        key = name.lower().strip()
        return self.alias_map.get(key)  # None drops people not on the roster

    @staticmethod
    def _build_alias_map(roster: dict) -> dict:
        out = {}
        for canonical, aliases in roster.items():
            out[canonical.lower()] = canonical
            for a in aliases or []:
                out[a.lower()] = canonical
        return out

    # ── day counting ──────────────────────────────────────────────────────
    def _count_days(self, ev: RawEvent) -> float:
        start_d = ev.start.date()
        # All-day events end at midnight of the day AFTER the last day.
        end_d = (ev.end - timedelta(seconds=1)).date()

        if start_d == end_d:
            if not ev.all_day and 0 < ev.duration_hours <= self.half_day_max_hours:
                return 0.5 if self._is_workday(start_d) else 0.0
            return 1.0 if self._is_workday(start_d) else 0.0

        days = 0.0
        d = start_d
        while d <= end_d:
            if self._is_workday(d):
                days += 1.0
            d += timedelta(days=1)
        return days

    def _is_workday(self, d: date) -> bool:
        if self.skip_weekends and d.weekday() >= 5:  # 5 Sat, 6 Sun
            return False
        if d in self.holidays:
            return False
        return True

    @staticmethod
    def _as_date(value) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), "%Y-%m-%d").date()
