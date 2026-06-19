"""CLI entry point: read shared calendar -> parse PTO -> write Excel.

Usage:
  python -m src.main --start 2026-06-01 --end 2026-12-31 --out pto_report.xlsx
  python -m src.main --start 2026-06-01 --end 2026-12-31 --dry-run
"""
from __future__ import annotations

import argparse
from datetime import datetime

from .config import load_config
from .connector.outlook_com import OutlookComConnector
from .excel_writer import write_report
from .pto_parser import PtoParser


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def build_connector(cfg: dict):
    # Single backend today; swap here when the Graph connector lands.
    return OutlookComConnector(cfg.get("calendar", {}))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract team PTO from a shared Outlook calendar.")
    ap.add_argument("--start", type=_parse_date, help="YYYY-MM-DD (default: Jan 1 this year)")
    ap.add_argument("--end", type=_parse_date, help="YYYY-MM-DD (default: Dec 31 this year)")
    ap.add_argument("--out", default=None, help="output .xlsx path (overrides config)")
    ap.add_argument("--config", default=None, help="path to config.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="print parsed PTO and skipped events; write nothing")
    args = ap.parse_args(argv)

    # Default to the current calendar year so scheduled runs need no date args.
    today = datetime.now()
    start = args.start or datetime(today.year, 1, 1)
    end = args.end or datetime(today.year, 12, 31)

    cfg = load_config(args.config)

    connector = build_connector(cfg)
    events = connector.get_events(start, end)
    print(f"Read {len(events)} raw event(s) from the shared calendar.")

    parser = PtoParser(cfg)
    entries, skipped = parser.parse(events)
    print(f"Parsed {len(entries)} PTO entr(ies); skipped {len(skipped)}.")

    if args.dry_run:
        _print_dry_run(entries, skipped)
        return 0

    out_path = args.out or cfg.get("output", {}).get("path", "pto_report.xlsx")
    write_report(entries, out_path, start, end)
    print(f"Wrote report: {out_path}")
    return 0


def _print_dry_run(entries, skipped):
    print("\n=== PTO ENTRIES ===")
    for e in sorted(entries, key=lambda x: (x.person, x.start)):
        print(f"  {e.person:<20} {e.start:%Y-%m-%d} -> {e.end:%Y-%m-%d}  "
              f"{e.days:>4} d  [{e.pto_type}]  {e.note}")
    print("\n=== SKIPPED (not PTO or no person) ===")
    for ev in skipped:
        print(f"  {ev.start:%Y-%m-%d}  busy={ev.busy_status}  "
              f"cats={ev.categories}  {ev.subject!r}")


if __name__ == "__main__":
    raise SystemExit(main())
