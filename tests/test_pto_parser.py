"""Parser tests — pure logic, no Outlook/pywin32 required.

    python -m pytest tests/        (or)        python tests/test_pto_parser.py
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config
from src.models import RawEvent
from src.pto_parser import PtoParser


def make_parser():
    return PtoParser(load_config())


def ev(subject, start, end, all_day=False, busy=None, cats=None, org=""):
    return RawEvent(subject=subject, start=start, end=end, all_day=all_day,
                    organizer=org, categories=cats or [], busy_status=busy)


def test_subject_name_and_single_day():
    p = make_parser()
    e = ev("Sally - PTO", datetime(2026, 6, 22, 0, 0), datetime(2026, 6, 23, 0, 0),
           all_day=True)
    entries, skipped = p.parse([e])
    assert len(entries) == 1
    assert entries[0].person == "Sally"
    assert entries[0].days == 1.0


def test_multi_day_skips_weekend():
    p = make_parser()
    # Fri 2026-06-19 .. Mon 2026-06-22 inclusive (all-day end = midnight 06-23)
    e = ev("John: Vacation", datetime(2026, 6, 19, 0, 0), datetime(2026, 6, 23, 0, 0),
           all_day=True)
    entries, _ = p.parse([e])
    assert entries[0].days == 2.0  # Fri + Mon, Sat/Sun skipped


def test_half_day_timed():
    p = make_parser()
    e = ev("Sally OOO", datetime(2026, 6, 22, 9, 0), datetime(2026, 6, 22, 12, 0))
    entries, _ = p.parse([e])
    assert entries[0].days == 0.5


def test_out_of_office_without_keyword():
    p = make_parser()
    e = ev("Dentist", datetime(2026, 6, 22, 0, 0), datetime(2026, 6, 23, 0, 0),
           all_day=True, busy=3, org="Maria Lopez")
    entries, _ = p.parse([e])
    assert entries and entries[0].person == "Maria Lopez"


def test_non_pto_skipped():
    p = make_parser()
    e = ev("Sprint planning", datetime(2026, 6, 22, 10, 0), datetime(2026, 6, 22, 11, 0),
           busy=2)
    entries, skipped = p.parse([e])
    assert not entries and len(skipped) == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} test(s) passed.")
