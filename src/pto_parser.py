"""Turn RawEvents from the shared calendar into normalized PtoEntry records.

Two jobs, in order:
  1. Is this event PTO?      (categories / subject patterns / OOF busy status)
  2. Who is it for?          (subject regex -> organizer)  + roster canonicalize
Then count business days, honoring weekends, company holidays, and half-days.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta

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
        """Business days of PTO, robust to how the event was entered.

        - All-day events: count business days midnight-to-midnight (exact).
        - Timed events <= 24h (incl. overnight/timezone artifacts): a single
          shift -> 1 day (0.5 if within the half-day threshold), attributed to
          the business day holding most of its hours. Avoids double-counting an
          event that merely straddles midnight.
        - Timed events > 24h: a genuine multi-day range -> business days covered.
        """
        if ev.duration_hours <= 0:
            d = ev.start.date()
            return 1.0 if self._is_workday(d) else 0.0

        if ev.all_day:
            # All-day events end at midnight of the day AFTER the last day.
            return self._business_days(ev.start.date(), (ev.end - timedelta(seconds=1)).date())

        if ev.duration_hours <= 24:
            day = self._majority_workday(ev)
            if day is None:
                return 0.0
            return 0.5 if ev.duration_hours <= self.half_day_max_hours else 1.0

        return self._business_days(ev.start.date(), (ev.end - timedelta(seconds=1)).date())

    def _business_days(self, start_d: date, end_d: date) -> float:
        days = 0.0
        d = start_d
        while d <= end_d:
            if self._is_workday(d):
                days += 1.0
            d += timedelta(days=1)
        return days

    def _majority_workday(self, ev: RawEvent) -> date | None:
        """The business day that holds the most of this event's hours.
        Returns None if the event touches no business day."""
        hours: dict[date, float] = defaultdict(float)
        cur = ev.start
        while cur < ev.end:
            next_midnight = datetime.combine(cur.date() + timedelta(days=1), time.min)
            seg_end = min(ev.end, next_midnight)
            hours[cur.date()] += (seg_end - cur).total_seconds() / 3600.0
            cur = seg_end
        workdays = {d: h for d, h in hours.items() if self._is_workday(d)}
        if not workdays:
            return None
        return max(workdays, key=workdays.get)

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
