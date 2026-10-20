"""
Time Normalization Logic (v2)

Mengubah ekspresi waktu bahasa Indonesia menjadi objek datetime.

Perubahan utama dibanding v1:
- Hasil NER (``entities``) benar-benar dipakai: parsing dicoba pada teks entitas
  lebih dulu, lalu fallback ke teks penuh (pendekatan hybrid NER + rule-based).
- Angka dalam kata ("sepuluh", "dua belas", "tiga puluh") dikonversi ke digit.
- Ekspresi sehari-hari: "setengah 8", "jam 7 kurang 15", "jam 9 lewat 15",
  "setengah jam lagi", "sejam lagi", "dalam 10 menit".
- Offset hari/minggu ("3 hari lagi", "2 minggu lagi") dan "minggu/pekan depan".
- "minggu depan" tidak lagi salah dibaca sebagai hari Minggu.
- Konteks pagi/siang/sore/malam lebih akurat ("jam 2 sore" -> 14:00).
- ``normalize(..., now=...)`` menerima waktu acuan sehingga bisa diuji secara
  deterministik.

Kebijakan: jika tidak ada tanggal eksplisit (besok, lusa, nama hari, ...) dan
waktu yang diminta sudah lewat hari ini, reminder digeser ke besok.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytz

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Angka dalam kata -> digit
# ---------------------------------------------------------------------------

_UNITS = {
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9,
}
_NUMBER_VOCAB = set(_UNITS) | {"sepuluh", "sebelas", "belas", "puluh"}


def _convert_run(words: List[str]) -> List[str]:
    """Ubah satu rangkaian kata bilangan menjadi daftar token (digit/aslinya)."""
    out: List[str] = []
    i, n = 0, len(words)
    while i < n:
        w = words[i]
        nxt = words[i + 1] if i + 1 < n else None
        if w == "sepuluh":
            out.append("10")
            i += 1
        elif w == "sebelas":
            out.append("11")
            i += 1
        elif w in _UNITS:
            u = _UNITS[w]
            if nxt == "belas":
                out.append(str(u + 10))
                i += 2
            elif nxt == "puluh":
                value = u * 10
                i += 2
                if i < n and words[i] in _UNITS and (
                        i + 1 >= n or words[i + 1] not in ("belas", "puluh")):
                    value += _UNITS[words[i]]
                    i += 1
                out.append(str(value))
            else:
                out.append(str(u))
                i += 1
        else:  # "belas"/"puluh" tanpa pasangan: biarkan apa adanya
            out.append(w)
            i += 1
    return out


def words_to_digits(text: str) -> str:
    """'jam dua belas siang' -> 'jam 12 siang'; 'tiga puluh menit' -> '30 menit'."""
    tokens = text.split()
    result: List[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] in _NUMBER_VOCAB:
            j = i
            while j < len(tokens) and tokens[j] in _NUMBER_VOCAB:
                j += 1
            result.extend(_convert_run(tokens[i:j]))
            i = j
        else:
            result.append(tokens[i])
            i += 1
    return " ".join(result)


# ---------------------------------------------------------------------------
# Konstanta
# ---------------------------------------------------------------------------

_DAY_NUM = {
    "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
    "jumat": 4, "jum'at": 4, "sabtu": 5, "minggu": 6,
}
_DAY_RE = re.compile(r"\b(senin|selasa|rabu|kamis|jumat|jum'at|sabtu|minggu)\b")
_WEEK_PHRASE_RE = re.compile(r"\b(?:minggu|pekan)\s+(depan|ini|lalu)\b")

_REL_SECONDS = {"detik": 1, "menit": 60, "jam": 3600}
_REL_UNIT_RE = r"(detik|menit|jam|hari|minggu|pekan)"
_REL_PATTERNS = [
    re.compile(r"(\d+)\s*" + _REL_UNIT_RE + r"\s*(?:lagi|ke\s*depan|dari\s*sekarang)"),
    re.compile(r"dalam\s*(\d+)\s*" + _REL_UNIT_RE),
]
_REL_FIXED = [
    (re.compile(r"setengah\s*jam\s*(?:lagi|ke\s*depan)"), ("jam", 0.5)),
    (re.compile(r"\bsejam\s*lagi"), ("jam", 1)),
    (re.compile(r"\bsemenit\s*lagi"), ("menit", 1)),
    (re.compile(r"\bsehari\s*lagi"), ("hari", 1)),
]
_UNIT_TO_SECONDS = {"detik": 1, "menit": 60, "jam": 3600,
                    "hari": 86400, "minggu": 604800}

_PART_OF_DAY_DEFAULT = {"pagi": 8, "siang": 12, "sore": 16, "malam": 19}


class TimeNormalizer:
    """Normalize extracted time entities to datetime"""

    def __init__(self, timezone: str = "Asia/Jakarta"):
        self.timezone = pytz.timezone(timezone)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def normalize(self, text: str, entities: Optional[List[Dict]] = None,
                  now: Optional[datetime] = None) -> datetime:
        """
        Args:
            text: input asli pengguna.
            entities: entitas dari model NER (opsional). Dipakai sebagai
                sumber parsing prioritas pertama.
            now: waktu acuan (aware). Default: waktu saat ini.
        """
        now = now or datetime.now(self.timezone)
        full = self._prepare(text)
        entity_text = self._prepare(" ".join(
            e.get("text", "") for e in (entities or [])))
        sources = [s for s in (entity_text, full) if s]
        if full not in sources:
            sources.append(full)

        # 1) Relatif: "X detik/menit/jam lagi" langsung dihitung dari now.
        #    "X hari/minggu lagi" menjadi offset tanggal; jam boleh ditentukan.
        day_offset_seconds = 0
        for src in sources:
            rel = self._extract_relative(src)
            if rel is None:
                continue
            unit, amount = rel
            seconds = amount * _UNIT_TO_SECONDS[unit]
            if unit in _REL_SECONDS:
                logger.debug("relative: +%s s", seconds)
                return now + timedelta(seconds=seconds)
            day_offset_seconds = seconds
            break

        # 2) Komponen waktu & tanggal
        time_parts = self._first(sources, self._extract_time)
        date_dt = self._first(sources, lambda s: self._determine_date(s, now))
        if day_offset_seconds:
            date_dt = now + timedelta(seconds=day_offset_seconds)

        if time_parts is not None:
            hour, minute = time_parts
            hour = self._adjust_hour_by_context(full, hour)
        else:
            pod = self._first(sources, self._part_of_day_hour)
            if pod is not None:
                hour, minute = pod, 0
            elif day_offset_seconds:
                return date_dt  # "3 hari lagi": pertahankan jam sekarang
            else:
                hour, minute = 9, 0

        base = date_dt if date_dt is not None else now
        try:
            result = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError as e:
            logger.warning("invalid time (%s), fallback +1h", e)
            return now + timedelta(hours=1)

        if date_dt is None and result <= now:
            result += timedelta(days=1)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _first(sources, fn):
        for s in sources:
            value = fn(s)
            if value is not None:
                return value
        return None

    @staticmethod
    def _prepare(text: str) -> str:
        t = (text or "").lower().strip()
        # artefak tokenizer: "12 . 30" / "12 : 30" -> "12.30"
        t = re.sub(r"(\d)\s*([.:,])\s*(\d)", r"\1\2\3", t)
        t = re.sub(r"\s+", " ", t)
        return words_to_digits(t)

    @staticmethod
    def _extract_relative(text: str) -> Optional[Tuple[str, float]]:
        for pattern, (unit, amount) in _REL_FIXED:
            if pattern.search(text):
                return unit, amount
        for pattern in _REL_PATTERNS:
            m = pattern.search(text)
            if m:
                unit = m.group(2)
                return ("minggu" if unit == "pekan" else unit), int(m.group(1))
        return None

    @staticmethod
    def _extract_time(text: str) -> Optional[Tuple[int, int]]:
        # "setengah 8" -> 07:30
        m = re.search(r"setengah\s*(\d{1,2})(?!\d)", text)
        if m:
            n = int(m.group(1))
            return (n - 1 if n > 1 else 12), 30

        # "7 kurang 15 [menit]" -> 06:45, "7 kurang seperempat" -> 06:45
        m = re.search(r"(\d{1,2})\s*kurang\s*(\d{1,2})(?!\d)", text)
        if m:
            n, mins = int(m.group(1)), int(m.group(2))
            if 0 < mins < 60:
                return (n - 1 if n > 1 else 12), 60 - mins
        m = re.search(r"(\d{1,2})\s*kurang\s*seperempat", text)
        if m:
            n = int(m.group(1))
            return (n - 1 if n > 1 else 12), 45

        # "9 lewat 15 [menit]" -> 09:15
        m = re.search(r"(\d{1,2})\s*lewat\s*(\d{1,2})(?!\d)", text)
        if m and 0 <= int(m.group(2)) < 60:
            return int(m.group(1)), int(m.group(2))

        # "09:30", "9.30", "14,00"
        m = re.search(r"(?<!\d)(\d{1,2})[:.,](\d{2})(?!\d)", text)
        if m and int(m.group(1)) <= 24 and int(m.group(2)) < 60:
            return int(m.group(1)), int(m.group(2))

        # "jam 9", "pukul 14"
        m = re.search(r"(?:pukul|jam)\s*(\d{1,2})(?!\d)", text)
        if m:
            return int(m.group(1)), 0

        # "7 pagi", "3 sore"
        m = re.search(r"(?<!\d)(\d{1,2})\s*(?:pagi|siang|sore|malam)", text)
        if m:
            return int(m.group(1)), 0
        return None

    @staticmethod
    def _part_of_day_hour(text: str) -> Optional[int]:
        for word, hour in _PART_OF_DAY_DEFAULT.items():
            if re.search(r"\b" + word + r"\b", text):
                return hour
        return None

    @staticmethod
    def _determine_date(text: str, now: datetime) -> Optional[datetime]:
        """Tanggal target, atau None jika tidak ada penanda tanggal."""
        week_ref = _WEEK_PHRASE_RE.search(text)
        next_week = bool(week_ref and week_ref.group(1) == "depan")
        cleaned = _WEEK_PHRASE_RE.sub(" ", text)

        if re.search(r"\bbesok\b", cleaned):
            return now + timedelta(days=1)
        if re.search(r"\blusa\b", cleaned):
            return now + timedelta(days=2)
        if re.search(r"\bkemarin\b", cleaned):
            return now - timedelta(days=1)

        m = _DAY_RE.search(cleaned)
        if m:
            day_num = _DAY_NUM[m.group(1)]
            if next_week:
                monday_next = now - timedelta(days=now.weekday()) + timedelta(days=7)
                return monday_next + timedelta(days=day_num)
            days_ahead = day_num - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return now + timedelta(days=days_ahead)

        if next_week:
            return now + timedelta(days=7)
        return None

    @staticmethod
    def _adjust_hour_by_context(text: str, hour: int) -> int:
        """Sesuaikan jam 12-jam ke 24-jam berdasarkan pagi/siang/sore/malam."""
        if hour >= 13:
            return hour

        def has(word: str) -> bool:
            return re.search(r"\b" + word + r"\b", text) is not None

        if has("malam"):
            if hour == 12:
                return 0
            if 6 <= hour <= 11:
                return hour + 12
            if 1 <= hour <= 5:
                return hour
            return 19
        if has("sore"):
            if 1 <= hour <= 6:
                return hour + 12
            return 16
        if has("siang"):
            if hour in (10, 11, 12):
                return hour
            if 1 <= hour <= 4:
                return hour + 12
            return 12
        if has("pagi"):
            if 1 <= hour <= 11:
                return hour
            return 8
        return hour
