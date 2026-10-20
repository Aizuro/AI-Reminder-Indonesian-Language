"""
Evaluasi model NER reminder pada test set berlabel.

Metrik (level entitas, exact match pada tipe + teks):
  - Precision / Recall / F1 (micro dan per tipe entitas)
  - Sentence exact match (semua entitas kalimat benar)
  - Rata-rata confidence untuk kalimat benar vs salah  -> menunjukkan apakah
    confidence score benar-benar berkorelasi dengan kebenaran
  - Latensi inferensi (rata-rata, p95)

Format data:
  --conll  file.conll : satu "token<spasi/tab>label" per baris, kalimat dipisah baris kosong
  --jsonl  file.jsonl : {"text": "...", "entities": [{"type": "TIME", "text": "jam 7 pagi"}]}

Dua jenis metrik entitas:
  1. Strict  : tipe + teks entitas harus sama persis (tergantung skema label & cara
               memotong entitas).
  2. Char    : F1 level karakter pada bagian kalimat yang ditandai sebagai ekspresi
               waktu. TIDAK bergantung pada nama label maupun batas entitas, jadi
               cocok jika skema label model berbeda dari gold.

Pemakaian:
    python evaluate_ner.py --jsonl tests/data/ner_testset.jsonl
    python evaluate_ner.py --jsonl tests/data/ner_testset.jsonl --type-map DATE=DAT,TIME=TIM
    python evaluate_ner.py --jsonl tests/data/ner_testset.jsonl --only-types DATE,TIME,DURATION
"""
import argparse
import json
import statistics
import time
from collections import defaultdict


def _norm(s: str) -> str:
    # buang spasi & huruf besar: output model memecah sub-word dengan spasi
    return "".join(s.lower().split())


def read_conll(path):
    samples, tokens, labels = [], [], []

    def flush():
        if tokens:
            samples.append({"text": " ".join(tokens),
                            "entities": _bio_to_entities(tokens, labels)})

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                flush()
                tokens, labels = [], []
                continue
            parts = line.split()
            tokens.append(parts[0])
            labels.append(parts[-1])
    flush()
    return samples


def _bio_to_entities(tokens, labels):
    ents, cur = [], None
    for tok, lab in zip(tokens, labels):
        if lab.startswith("B-") or (lab.startswith("I-") and cur is None):
            if cur:
                ents.append(cur)
            cur = {"type": lab[2:], "text": tok}
        elif lab.startswith("I-") and cur:
            cur["text"] += " " + tok
        else:
            if cur:
                ents.append(cur)
            cur = None
    if cur:
        ents.append(cur)
    return ents


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _keyset(entities, ignore_type):
    return {("*" if ignore_type else e["type"], _norm(e["text"])) for e in entities}


def _char_mask(text, entities):
    """Tandai karakter (tanpa spasi) yang tercakup entitas. Return (mask, n_unaligned)."""
    base = _norm(text)
    mask = [False] * len(base)
    cursor, unaligned = 0, 0
    for e in entities:
        t = _norm(e["text"])
        if not t:
            continue
        i = base.find(t, cursor)
        if i < 0:
            i = base.find(t)
        if i < 0:
            unaligned += 1
            continue
        for k in range(i, i + len(t)):
            mask[k] = True
        cursor = i + len(t)
    return mask, unaligned


def _prep(entities, type_map=None, only_types=None):
    out = []
    for e in entities:
        t = (type_map or {}).get(e["type"], e["type"])
        if only_types and t not in only_types:
            continue
        out.append({"type": t, "text": e["text"]})
    return out


def evaluate(predict_fn, samples, ignore_type=False, type_map=None, only_types=None,
             collect=False):
    """predict_fn(text) -> {'entities': [...], 'confidence': float}

    type_map  : ubah tipe gold ke nama label model, mis. {"TIME": "TIM"}
    only_types: batasi evaluasi ke tipe tertentu (setelah type_map), untuk gold & prediksi
    """
    tp = fp = fn = 0
    c_tp = c_fp = c_fn = unaligned = 0
    per_type = defaultdict(lambda: [0, 0, 0])  # tp, fp, fn
    exact = 0
    conf_ok, conf_bad, latencies = [], [], []
    records = []

    for s in samples:
        t0 = time.perf_counter()
        out = predict_fn(s["text"])
        latencies.append((time.perf_counter() - t0) * 1000)

        g_ents = _prep(s["entities"], type_map, only_types)
        p_ents = _prep(out["entities"], None, only_types)
        gold = _keyset(g_ents, ignore_type)
        pred = _keyset(p_ents, ignore_type)

        if collect:
            records.append({"text": s["text"], "match": gold == pred,
                            "gold": [[e["type"], e["text"]] for e in g_ents],
                            "pred": [[e["type"], e["text"]] for e in p_ents]})

        g_mask, u1 = _char_mask(s["text"], g_ents)
        p_mask, u2 = _char_mask(s["text"], p_ents)
        unaligned += u1 + u2
        for g, p_ in zip(g_mask, p_mask):
            c_tp += g and p_
            c_fp += p_ and not g
            c_fn += g and not p_
        for k in gold & pred:
            tp += 1
            per_type[k[0]][0] += 1
        for k in pred - gold:
            fp += 1
            per_type[k[0]][1] += 1
        for k in gold - pred:
            fn += 1
            per_type[k[0]][2] += 1
        if gold == pred:
            exact += 1
            conf_ok.append(out.get("confidence", float("nan")))
        else:
            conf_bad.append(out.get("confidence", float("nan")))

    def prf(tp_, fp_, fn_):
        p = tp_ / (tp_ + fp_) if tp_ + fp_ else 0.0
        r = tp_ / (tp_ + fn_) if tp_ + fn_ else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        return p, r, f

    p, r, f = prf(tp, fp, fn)
    cp, cr, cf = prf(c_tp, c_fp, c_fn)
    lat_sorted = sorted(latencies)
    p95 = lat_sorted[min(len(lat_sorted) - 1, int(0.95 * len(lat_sorted)))] if lat_sorted else 0.0
    mean = lambda xs: statistics.mean(xs) if xs else float("nan")  # noqa: E731
    return {
        "n_samples": len(samples),
        "precision": p, "recall": r, "f1": f,
        "char_precision": cp, "char_recall": cr, "char_f1": cf,
        "unaligned_entities": unaligned,
        "records": records,
        "per_type": {t: dict(zip(("precision", "recall", "f1"), prf(*v)),
                             support=v[0] + v[2]) for t, v in per_type.items()},
        "sentence_exact_match": exact / len(samples) if samples else 0.0,
        "mean_confidence_correct": mean(conf_ok),
        "mean_confidence_wrong": mean(conf_bad),
        "latency_ms_mean": mean(latencies),
        "latency_ms_p95": p95,
    }


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--conll")
    g.add_argument("--jsonl")
    ap.add_argument("--model", default="Aizuro/indonesian-ner-time_reminder")
    ap.add_argument("--ignore-type", action="store_true",
                    help="bandingkan hanya teks entitas, abaikan nama tipe")
    ap.add_argument("--type-map", default="",
                    help="ubah tipe gold ke label model, mis. DATE=DAT,TIME=TIM")
    ap.add_argument("--only-types", default="",
                    help="evaluasi hanya tipe ini (setelah type-map), mis. DATE,TIME")
    ap.add_argument("--show-errors", type=int, default=0, metavar="N",
                    help="tampilkan N kalimat pertama yang entitasnya tidak cocok (gold vs prediksi)")
    ap.add_argument("--dump-pred", metavar="FILE",
                    help="simpan semua prediksi model (jsonl) untuk dianalisis")
    ap.add_argument("--json-out")
    args = ap.parse_args()

    samples = read_conll(args.conll) if args.conll else read_jsonl(args.jsonl)
    from src.ner_model import ReminderNERModel
    model = ReminderNERModel(model_path=args.model)
    model.predict(samples[0]["text"])  # warm-up, tidak dihitung latensinya

    type_map = dict(kv.split("=", 1) for kv in args.type_map.split(",") if kv)
    only_types = {t for t in args.only_types.split(",") if t} or None
    res = evaluate(model.predict, samples, ignore_type=args.ignore_type,
                   type_map=type_map, only_types=only_types,
                   collect=bool(args.show_errors or args.dump_pred))
    print(f"Samples              : {res['n_samples']}")
    print(f"Entity P / R / F1    : {res['precision']:.3f} / {res['recall']:.3f} / {res['f1']:.3f}   (strict: tipe + teks)")
    print(f"Char   P / R / F1    : {res['char_precision']:.3f} / {res['char_recall']:.3f} / {res['char_f1']:.3f}   (tanpa label & batas entitas)")
    print(f"Sentence exact match : {res['sentence_exact_match']:.1%}")
    print(f"Mean confidence      : correct={res['mean_confidence_correct']:.3f}  wrong={res['mean_confidence_wrong']:.3f}")
    print(f"Latency (ms)         : mean={res['latency_ms_mean']:.1f}  p95={res['latency_ms_p95']:.1f}")
    print("\nPer tipe entitas:")
    for t, v in sorted(res["per_type"].items()):
        print(f"  {t:<14} P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f} (n={v['support']})")
    records = res.pop("records")
    if args.show_errors:
        bad = [r for r in records if not r["match"]][:args.show_errors]
        print(f"\nContoh ketidakcocokan ({len(bad)} pertama):")
        for r in bad:
            print(f"  {r['text']!r}\n      gold: {r['gold']}\n      pred: {r['pred']}")
    if args.dump_pred:
        with open(args.dump_pred, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
