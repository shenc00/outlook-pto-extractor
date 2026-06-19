"""Milestone 1 spike: prove COM can open the shared calendar and list events.

No PTO parsing, no Excel — just confirm the connection + date filter work and
eyeball what the raw events actually look like (subjects, categories, busy
status). Use this to tune config.yaml's pto/person rules.

    python scripts/spike_read_calendar.py --start 2026-06-01 --end 2026-12-31
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config            # noqa: E402
from src.connector.outlook_com import OutlookComConnector  # noqa: E402


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, type=_parse_date)
    ap.add_argument("--end", required=True, type=_parse_date)
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    conn = OutlookComConnector(cfg.get("calendar", {}))
    events = conn.get_events(args.start, args.end)

    print(f"\nFound {len(events)} event(s) in "
          f"{args.start:%Y-%m-%d}..{args.end:%Y-%m-%d}\n")
    for ev in events:
        flags = []
        if ev.all_day:
            flags.append("all-day")
        if ev.busy_status == 3:
            flags.append("OOF")
        print(f"  {ev.start:%Y-%m-%d %H:%M} -> {ev.end:%Y-%m-%d %H:%M}  "
              f"{'/'.join(flags):<14} cats={ev.categories} "
              f"org={ev.organizer!r}\n      {ev.subject!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
