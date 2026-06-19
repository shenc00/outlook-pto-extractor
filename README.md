# Outlook PTO Extractor

Reads a **shared team calendar** in Outlook and produces a formatted Excel
report of the team's PTO (paid time off) over a chosen date range.

## How it works

```
main.py (CLI)
   │  date range, output path
   ▼
connector/  ──► outlook_com.py   reads ONE shared team calendar via COM
   │            (graph_api.py — optional, later, for unattended runs)
   ▼  RawEvent records
pto_parser.py   figure out WHO each event belongs to + how many PTO days
   ▼  PtoEntry records
excel_writer.py  ──►  pto_report.xlsx  (Summary + Detail sheets)
```

The connector is swappable behind the `CalendarConnector` interface, so the
COM reader can later be replaced with a Microsoft Graph reader without touching
the parser or Excel code.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`pywin32` requires the desktop Outlook app to be installed and signed in, and
the shared team calendar must be added to your Outlook (under *Other Calendars*).

## Quick start

1. Edit `config.yaml` — set the shared calendar owner/name and PTO rules.
2. **Spike first** (proves COM works, lists raw events, no parsing):
   ```powershell
   python scripts/spike_read_calendar.py --start 2026-06-01 --end 2026-12-31
   ```
3. **Dry run** the parser (prints what it thinks is PTO, writes nothing):
   ```powershell
   python -m src.main --start 2026-06-01 --end 2026-12-31 --dry-run
   ```
4. **Generate the report**:
   ```powershell
   python -m src.main --start 2026-06-01 --end 2026-12-31 --out pto_report.xlsx
   ```

## Status / milestones

- [ ] M1 Spike — read shared calendar, dump raw events
- [ ] M2 Parser — extract person + PTO days, dry-run dump
- [ ] M3 Excel — Summary + Detail sheets
- [ ] M4 Config/CLI polish for full team
- [ ] M5 (optional) Graph connector for scheduled/unattended runs

See `PLAN.md` notes inline in code for the open decisions (subject-line format,
half-days, holidays).
