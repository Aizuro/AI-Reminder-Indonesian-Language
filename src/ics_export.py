"""
Ekspor reminder ke format iCalendar (.ics) agar bisa diimpor ke
Google Calendar / Outlook / Apple Calendar. Tanpa dependensi tambahan.
"""
from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional

import pytz

CRLF = "\r\n"


def _escape(text: str) -> str:
    """Escape sesuai RFC 5545 (backslash, titik koma, koma, newline)."""
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n"))


def _fold(line: str) -> str:
    """Lipat baris > 75 oktet (RFC 5545 §3.1) tanpa memotong karakter UTF-8."""
    if len(line.encode("utf-8")) <= 75:
        return line
    parts, current, size = [], "", 0
    for ch in line:
        ch_size = len(ch.encode("utf-8"))
        limit = 75 if not parts else 74  # baris lanjutan diawali 1 spasi
        if size + ch_size > limit:
            parts.append(current)
            current, size = ch, ch_size
        else:
            current += ch
            size += ch_size
    parts.append(current)
    return (CRLF + " ").join(parts)


def _utc(dt: datetime) -> str:
    return dt.astimezone(pytz.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(reminders: Iterable[Dict], duration_minutes: int = 15,
              now: Optional[datetime] = None) -> str:
    """
    Args:
        reminders: iterable dict dengan kunci ``id``, ``text``, ``normalized_time``
            (datetime aware).
        duration_minutes: durasi event di kalender.
        now: waktu pembuatan (DTSTAMP); default sekarang (UTC).
    """
    stamp = _utc(now or datetime.now(pytz.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Reminder Indonesian//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for r in reminders:
        start = r["normalized_time"]
        end = start + timedelta(minutes=duration_minutes)
        summary = _escape(r["text"].strip())
        lines += [
            "BEGIN:VEVENT",
            f"UID:{r['id']}@ai-reminder",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_utc(start)}",
            f"DTEND:{_utc(end)}",
            f"SUMMARY:{summary}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{summary}",
            "TRIGGER:-PT0M",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return CRLF.join(_fold(l) for l in lines) + CRLF
