from datetime import datetime

import pytz

from src.ics_export import build_ics

JKT = pytz.timezone("Asia/Jakarta")
STAMP = pytz.utc.localize(datetime(2026, 10, 19, 7, 0, 0))


def _reminder(text="rapat; bawa laptop, notulen", when=(2026, 10, 20, 7, 0), rid="abc12345"):
    return {"id": rid, "text": text, "normalized_time": JKT.localize(datetime(*when))}


def test_structure_and_crlf():
    ics = build_ics([_reminder()], now=STAMP)
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert ics.count("BEGIN:VEVENT") == 1 and ics.count("END:VEVENT") == 1
    assert "\n" not in ics.replace("\r\n", "")  # tidak ada LF telanjang


def test_times_are_converted_to_utc():
    ics = build_ics([_reminder()], duration_minutes=30, now=STAMP)
    assert "DTSTART:20261020T000000Z" in ics   # 07:00 WIB = 00:00 UTC
    assert "DTEND:20261020T003000Z" in ics
    assert "DTSTAMP:20261019T070000Z" in ics


def test_text_is_escaped():
    ics = build_ics([_reminder()], now=STAMP)
    assert r"SUMMARY:rapat\; bawa laptop\, notulen" in ics


def test_long_lines_are_folded_to_75_octets():
    ics = build_ics([_reminder(text="ingatkan " + "panjang " * 30)], now=STAMP)
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75


def test_multiple_reminders_and_alarm():
    ics = build_ics([_reminder(rid="a"), _reminder(rid="b", when=(2026, 10, 21, 9, 0))], now=STAMP)
    assert ics.count("BEGIN:VEVENT") == 2
    assert ics.count("BEGIN:VALARM") == 2
    assert "UID:a@ai-reminder" in ics and "UID:b@ai-reminder" in ics


def test_empty_list_is_valid_calendar():
    ics = build_ics([], now=STAMP)
    assert "BEGIN:VEVENT" not in ics and ics.startswith("BEGIN:VCALENDAR")
