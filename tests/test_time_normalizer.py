import json
from datetime import datetime
from pathlib import Path

import pytest
import pytz

from src.time_normalizer import TimeNormalizer, words_to_digits

DATA = Path(__file__).parent / "data"


def _load(name):
    d = json.loads((DATA / name).read_text(encoding="utf-8"))
    tz = pytz.timezone(d["timezone"])
    return d["cases"], tz.localize(datetime.fromisoformat(d["now"])), d["timezone"]


DEV_CASES, NOW, TZ = _load("normalizer_cases.json")
HOLDOUT_CASES, _, _ = _load("normalizer_holdout.json")
HOLDOUT_TYPICAL = [c for c in HOLDOUT_CASES if c["category"] == "typical"]
HOLDOUT_LIMITS = [c for c in HOLDOUT_CASES if c["category"] == "out_of_scope"]

normalizer = TimeNormalizer(TZ)


def _run(case, entities=None):
    return normalizer.normalize(case["text"], entities, now=NOW).strftime("%Y-%m-%dT%H:%M:%S")


@pytest.mark.parametrize("case", DEV_CASES, ids=lambda c: c["id"])
def test_dev_cases(case):
    assert _run(case) == case["expected"], case["text"]


@pytest.mark.parametrize("case", HOLDOUT_TYPICAL, ids=lambda c: c["id"])
def test_holdout_typical(case):
    assert _run(case) == case["expected"], case["text"]


@pytest.mark.parametrize("case", HOLDOUT_LIMITS, ids=lambda c: c["id"])
@pytest.mark.xfail(reason="Batasan yang diketahui (lihat README: Known limitations)", strict=True)
def test_known_limitations(case):
    assert _run(case) == case["expected"]


@pytest.mark.parametrize("raw, expected", [
    ("jam dua belas siang", "jam 12 siang"),
    ("tiga puluh menit lagi", "30 menit lagi"),
    ("dua puluh lima menit", "25 menit"),
    ("lima belas detik", "15 detik"),
    ("jam sepuluh", "jam 10"),
    ("sebelas", "11"),
    ("tidak ada angka", "tidak ada angka"),
])
def test_words_to_digits(raw, expected):
    assert words_to_digits(raw) == expected


def test_entities_are_used_first():
    # Teks penuh memuat dua waktu; entitas NER menunjuk yang benar.
    text = "dari jam 7 pagi tadi, ingatkan saya jam 9 malam"
    ents = [{"type": "TIME", "text": "jam 9 malam", "tokens": ["jam", "9", "malam"]}]
    with_ner = normalizer.normalize(text, ents, now=NOW)
    assert with_ner.hour == 21 and with_ner.minute == 0


def test_entity_tokenizer_artifacts_are_cleaned():
    ents = [{"type": "TIME", "text": "jam 12 . 30", "tokens": []}]
    r = normalizer.normalize("makan siang jam 12.30 besok", ents, now=NOW)
    assert (r.day, r.hour, r.minute) == (20, 12, 30)


def test_falls_back_to_full_text_when_entities_empty():
    r = normalizer.normalize("alarm 20 detik lagi", [], now=NOW)
    assert (r - NOW).total_seconds() == 20


def test_minggu_depan_is_not_sunday():
    r = normalizer.normalize("minggu depan jam 9 pagi", None, now=NOW)
    assert r.weekday() == NOW.weekday()  # tepat 7 hari lagi, bukan hari Minggu
    assert (r.date() - NOW.date()).days == 7


def test_now_defaults_to_current_time():
    r = normalizer.normalize("5 menit lagi")
    assert r > datetime.now(pytz.timezone(TZ))
