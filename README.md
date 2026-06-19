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
excel_writer.py  ──►  pto_report.xlsx  (one calendar tab per month)
```

The connector is swappable behind the `CalendarConnector` interface, so the
COM reader can later be replaced with a Microsoft Graph reader without touching
the parser or Excel code.

## Logging PTO (so the report picks it up)

PTO is read from the shared **ISC Analytics CoE BD** calendar. For the report to
count days correctly and place each name on the right date, log time off as
**all-day events** with a consistent subject. Steps (classic Outlook):

1. Open Outlook → **Calendar**, and tick the shared **ISC Analytics CoE BD**
   calendar in the left pane so you are adding to *it* (not your personal one).
2. Double-click the first day you are off (or **Home → New Appointment**).
3. Tick **All day event**.
4. In **Subject**, use `Firstname - Type` — e.g. `Sally - PTO` (convention below).
5. For multiple days, set the **End** date to your last day off (keep it all-day).
6. Set **Show As → Out of Office** (or **Tentative** if it is not yet confirmed).
7. **Save & Close**, and confirm it landed on the shared calendar.

### Naming convention

`Firstname - Type` — the text before the dash is the person; the type word marks
it as PTO.

| Subject example   | Person  | Result    |
|-------------------|---------|-----------|
| `Sally - PTO`     | Sally   | time off  |
| `John - Vacation` | John    | time off  |
| `Maria - Leave`   | Maria   | time off  |
| `Vikas M - OOO`   | Vikas M | time off  |

Recognised type words: **PTO, Vacation, Holiday, Leave, OOO** (case-insensitive).
A colon works in place of the dash too (`Sally: PTO`).

**Tips**
- **The subject name is required.** On a shared calendar the organiser is the
  calendar itself (not the person), so the `Firstname - Type` subject is the only
  reliable way the report knows whose PTO it is — always include it.
- **One person per entry.** If two people are off the same day, create two
  separate events; both appear in that day's cell.
- **Half day?** Do *not* tick All day — create a timed event of 5 hours or less
  (e.g. 09:00–12:00). It counts as **0.5** of a day.
- **Tentative** entries (Show As → Tentative) appear with a `(tentative)` suffix.
- Weekends and out-of-month days are never counted; multi-day spans skip weekends.

## Setup

**One-click:** double-click **`setup.bat`** (or run it from a terminal). It
finds Python 3.11+, creates `.venv`, and installs all dependencies. Then
activate the venv for your session:

```powershell
.\.venv\Scripts\Activate.ps1
```

**Manual equivalent:**

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
4. **Generate the report** — one-click: double-click **`run.bat`** (it prompts
   for the date range and opens the result). Or from the terminal:
   ```powershell
   python -m src.main --start 2026-06-01 --end 2026-12-31 --out pto_report.xlsx
   ```

## Automated daily refresh on a VM (COM + OneDrive sync)

Run the report every weekday morning on a VM and publish it to SharePoint —
without any Azure app registration. The script writes the workbook into a
**OneDrive-synced copy of the SharePoint folder**, and the sync client uploads
it. Outlook COM needs a live desktop session, so the task runs **interactively**
and the VM uses **auto-logon**.

Target SharePoint location:
*GSC Transformation* → **Shared Documents** → `General / DOMAINS & PROJECTS / DELIVER Domain`.

### One-time VM setup

1. **Base install**: copy/clone this repo to the VM, run `setup.bat`, sign in to
   the **Outlook desktop app**, and add the shared **ISC Analytics CoE BD**
   calendar (see [Setup](#setup)).
2. **Auto-logon**: configure the VM to log the service user on automatically at
   boot (so an interactive session always exists for Outlook). Don't *sign out*
   after — locking the screen is fine; signing out kills the session.
3. **Sync the SharePoint folder**: open the SharePoint library in a browser,
   navigate to the **DELIVER Domain** folder, and click **Sync** (or *Add
   shortcut to OneDrive*). It now appears locally under your OneDrive, e.g.
   `C:\Users\<vmuser>\OneDrive - BD\...\DELIVER Domain`. Note that full path.
4. **Point output at the synced folder** — create `config.local.yaml` (gitignored)
   next to `config.yaml`:
   ```yaml
   output:
     path: "C:/Users/<vmuser>/OneDrive - BD/.../DELIVER Domain/pto_report.xlsx"
   ```
5. **Register the scheduled task** (elevated PowerShell, once):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\register_scheduled_task.ps1 -At 06:00
   ```
   This creates *“PTO Report Daily Refresh”* running **Mon–Fri at 06:00** in the
   interactive session.

### Verify

```powershell
Start-ScheduledTask -TaskName "PTO Report Daily Refresh"
# then check the newest log:
Get-ChildItem logs | Sort-Object LastWriteTime | Select-Object -Last 1 | Get-Content
```
Confirm `pto_report.xlsx` appears in the synced folder and turns green (synced)
in File Explorer / shows up in SharePoint.

The scheduled command needs no dates — it defaults to the **current calendar
year** (Jan 1 – Dec 31). Logs are written to `logs\refresh_<timestamp>.log`.

> **Why interactive + auto-logon?** Outlook COM cannot run in Windows session 0
> ("run whether the user is logged on or not"). The task must run in the live
> desktop session, which is why auto-logon is required.

## Status / milestones

- [ ] M1 Spike — read shared calendar, dump raw events
- [ ] M2 Parser — extract person + PTO days, dry-run dump
- [x] M3 Excel — one calendar tab per month (Mon..Sun grid, names per day)
- [ ] M4 Config/CLI polish for full team
- [x] M5 Scheduled daily refresh on a VM (COM + OneDrive sync to SharePoint)
- [ ] M6 (optional) Graph connector for fully unattended (no interactive session)

See `PLAN.md` notes inline in code for the open decisions (subject-line format,
half-days, holidays).
