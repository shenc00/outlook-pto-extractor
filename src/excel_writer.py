"""Write PtoEntry records to a formatted .xlsx with Summary + Detail sheets."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import PtoEntry

HEADER_FILL = PatternFill("solid", fgColor="305496")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FONT = Font(bold=True)
DATE_FMT = "yyyy-mm-dd"


def write_report(
    entries: list[PtoEntry],
    out_path: str,
    start: datetime,
    end: datetime,
) -> str:
    wb = Workbook()
    _write_summary(wb.active, entries, start, end)
    _write_detail(wb.create_sheet("Detail"), entries)
    wb.save(out_path)
    return out_path


def _write_summary(ws, entries: list[PtoEntry], start, end):
    ws.title = "Summary"
    ws["A1"] = "Team PTO Summary"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Range: {start:%Y-%m-%d} to {end:%Y-%m-%d}"
    ws["A3"] = f"Generated: {datetime.now():%Y-%m-%d %H:%M}"

    headers = ["Person", "Total PTO days", "# Entries"]
    row0 = 5
    _write_headers(ws, headers, row0)

    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for e in entries:
        totals[e.person] += e.days
        counts[e.person] += 1

    r = row0 + 1
    for person in sorted(totals):
        ws.cell(r, 1, person)
        ws.cell(r, 2, round(totals[person], 1))
        ws.cell(r, 3, counts[person])
        r += 1

    ws.cell(r, 1, "TOTAL").font = TOTAL_FONT
    c = ws.cell(r, 2, round(sum(totals.values()), 1)); c.font = TOTAL_FONT
    c = ws.cell(r, 3, sum(counts.values())); c.font = TOTAL_FONT

    _finish(ws, headers, row0, freeze=f"A{row0 + 1}")


def _write_detail(ws, entries: list[PtoEntry]):
    headers = ["Person", "Start", "End", "Days", "Type", "Note"]
    row0 = 1
    _write_headers(ws, headers, row0)

    r = row0 + 1
    for e in sorted(entries, key=lambda x: (x.person, x.start)):
        ws.cell(r, 1, e.person)
        cs = ws.cell(r, 2, e.start); cs.number_format = DATE_FMT
        ce = ws.cell(r, 3, e.end);   ce.number_format = DATE_FMT
        ws.cell(r, 4, round(e.days, 1))
        ws.cell(r, 5, e.pto_type)
        ws.cell(r, 6, e.note)
        r += 1

    _finish(ws, headers, row0, freeze=f"A{row0 + 1}")


# ── shared formatting helpers ─────────────────────────────────────────────
def _write_headers(ws, headers, row):
    for col, name in enumerate(headers, start=1):
        c = ws.cell(row, col, name)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center")


def _finish(ws, headers, header_row, freeze):
    ws.freeze_panes = freeze
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{header_row}"
    for col in range(1, len(headers) + 1):
        letter = get_column_letter(col)
        width = max(
            (len(str(c.value)) for c in ws[letter] if c.value is not None),
            default=10,
        )
        ws.column_dimensions[letter].width = min(max(width + 2, 12), 45)
