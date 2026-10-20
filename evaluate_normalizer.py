"""
Evaluasi end-to-end normalisasi waktu (teks Indonesia -> datetime).

Metrik: exact match terhadap ground truth yang ditulis manual
(tests/data/normalizer_cases.json), dengan waktu acuan ``now`` dibekukan agar
hasilnya deterministik. Dilaporkan per kategori + daftar kegagalan.

Pemakaian:
    python evaluate_normalizer.py                 # hanya komponen rule-based
    python evaluate_normalizer.py --with-ner      # pipeline penuh: NER -> normalizer
    python evaluate_normalizer.py --markdown      # tabel siap tempel ke README
"""
import argparse
import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import pytz

from src.time_normalizer import TimeNormalizer

DATA_PATH = Path(__file__).parent / "tests" / "data" / "normalizer_cases.json"


def load_cases(path: Path = DATA_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tz = pytz.timezone(data["timezone"])
    now = tz.localize(datetime.fromisoformat(data["now"]))
    return data["cases"], now, data["timezone"]


def evaluate(cases, now, timezone, entity_fn=None):
    normalizer = TimeNormalizer(timezone)
    per_cat = OrderedDict()
    failures = []
    for c in cases:
        entities = entity_fn(c["text"]) if entity_fn else []
        pred = normalizer.normalize(c["text"], entities, now=now)
        pred_s = pred.strftime("%Y-%m-%dT%H:%M:%S")
        ok = pred_s == c["expected"]
        stat = per_cat.setdefault(c["category"], [0, 0])
        stat[0] += int(ok)
        stat[1] += 1
        if not ok:
            failures.append({**c, "predicted": pred_s})
    return per_cat, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_PATH))
    ap.add_argument("--with-ner", action="store_true",
                    help="jalankan model NER dari Hugging Face dan kirim entitasnya ke normalizer")
    ap.add_argument("--model", default="Aizuro/indonesian-ner-time_reminder")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    cases, now, tzname = load_cases(Path(args.data))
    entity_fn = None
    if args.with_ner:
        from src.ner_model import ReminderNERModel
        model = ReminderNERModel(model_path=args.model)
        entity_fn = lambda t: model.predict(t)["entities"]  # noqa: E731

    per_cat, failures = evaluate(cases, now, tzname, entity_fn)
    total = sum(n for _, n in per_cat.values())
    correct = sum(k for k, _ in per_cat.values())
    mode = "NER + rule-based" if args.with_ner else "rule-based saja (tanpa NER)"
    print(f"Mode: {mode} | now = {now.isoformat()}")

    if args.markdown:
        print("\n| Kategori | Benar | Total | Akurasi |\n|---|---|---|---|")
        for cat, (k, n) in per_cat.items():
            print(f"| {cat} | {k} | {n} | {k / n:.1%} |")
        print(f"| **Total** | **{correct}** | **{total}** | **{correct / total:.1%}** |")
    else:
        print(f"\nExact-match accuracy: {correct}/{total} = {correct / total:.1%}\n")
        for cat, (k, n) in per_cat.items():
            print(f"  {cat:<16} {k:>3}/{n:<3} {k / n:6.1%}")

    if failures:
        print(f"\nKegagalan ({len(failures)}):")
        for f in failures:
            print(f"  [{f['id']}] {f['text']!r}\n      expected  {f['expected']}\n      predicted {f['predicted']}")


if __name__ == "__main__":
    main()
