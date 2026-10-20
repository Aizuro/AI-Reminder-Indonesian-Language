"""Menguji logika metrik evaluate_ner.py dengan model palsu (tanpa torch)."""
import math

from evaluate_ner import _bio_to_entities, evaluate

SAMPLES = [
    {"text": "ingatkan besok jam 7 pagi", "entities": [
        {"type": "DATE", "text": "besok"}, {"type": "TIME", "text": "jam 7 pagi"}]},
    {"text": "alarm 20 detik lagi", "entities": [{"type": "TIME", "text": "20 detik lagi"}]},
    {"text": "rapat kamis", "entities": [{"type": "DATE", "text": "kamis"}]},
]
PREDICTIONS = {
    # benar semua (spasi sub-word & huruf besar harus ditoleransi)
    SAMPLES[0]["text"]: {"entities": [{"type": "DATE", "text": "bes ok"},
                                      {"type": "TIME", "text": "Jam 7 pagi"}], "confidence": 0.99},
    # salah: batas entitas keliru -> 1 FP + 1 FN
    SAMPLES[1]["text"]: {"entities": [{"type": "TIME", "text": "20 detik"}], "confidence": 0.98},
    # salah: entitas tidak terdeteksi -> 1 FN
    SAMPLES[2]["text"]: {"entities": [], "confidence": 0.97},
}


def fake_predict(text):
    return PREDICTIONS[text]


def test_micro_prf_and_exact_match():
    r = evaluate(fake_predict, SAMPLES)
    # tp=2, fp=1, fn=2
    assert math.isclose(r["precision"], 2 / 3)
    assert math.isclose(r["recall"], 2 / 4)
    assert math.isclose(r["f1"], 2 * (2 / 3) * 0.5 / ((2 / 3) + 0.5))
    assert math.isclose(r["sentence_exact_match"], 1 / 3)


def test_per_type_breakdown():
    r = evaluate(fake_predict, SAMPLES)
    assert r["per_type"]["DATE"]["support"] == 2 and r["per_type"]["TIME"]["support"] == 2
    assert math.isclose(r["per_type"]["DATE"]["recall"], 1 / 2)


def test_confidence_split_by_correctness():
    r = evaluate(fake_predict, SAMPLES)
    assert math.isclose(r["mean_confidence_correct"], 0.99)
    assert math.isclose(r["mean_confidence_wrong"], 0.975)


def test_ignore_type():
    swapped = {SAMPLES[0]["text"]: {"entities": [{"type": "X", "text": "besok"},
                                                 {"type": "Y", "text": "jam 7 pagi"}], "confidence": 1.0}}
    r = evaluate(lambda t: swapped[t], SAMPLES[:1], ignore_type=True)
    assert r["f1"] == 1.0


def test_bio_to_entities():
    toks = ["ingatkan", "besok", "jam", "7", "pagi"]
    labs = ["O", "B-DATE", "B-TIME", "I-TIME", "I-TIME"]
    assert _bio_to_entities(toks, labs) == [
        {"type": "DATE", "text": "besok"}, {"type": "TIME", "text": "jam 7 pagi"}]


# --- metrik char-level, type-map, only-types, dan test set yang dibangun ---
import json
from pathlib import Path


def test_char_level_ignores_labels_and_boundaries():
    # model memotong "jam 7 pagi" jadi dua entitas dengan label lain -> char-level tetap sempurna
    pred = {SAMPLES[0]["text"]: {"entities": [{"type": "FOO", "text": "besok"},
                                              {"type": "BAR", "text": "jam"},
                                              {"type": "BAR", "text": "7 pagi"}], "confidence": 1.0}}
    r = evaluate(lambda t: pred[t], SAMPLES[:1])
    assert r["f1"] == 0.0                      # strict gagal
    assert math.isclose(r["char_f1"], 1.0)     # char-level tidak terpengaruh


def test_type_map_and_only_types():
    pred = {SAMPLES[0]["text"]: {"entities": [{"type": "DAT", "text": "besok"},
                                              {"type": "TIM", "text": "jam 7 pagi"},
                                              {"type": "PER", "text": "ingatkan"}], "confidence": 1.0}}
    r = evaluate(lambda t: pred[t], SAMPLES[:1], type_map={"DATE": "DAT", "TIME": "TIM"})
    assert r["precision"] < 1.0                # entitas PER dihitung sebagai false positive
    r = evaluate(lambda t: pred[t], SAMPLES[:1], type_map={"DATE": "DAT", "TIME": "TIM"},
                 only_types={"DAT", "TIM"})
    assert r["f1"] == 1.0


def test_generated_testset_is_consistent_and_oracle_scores_one():
    path = Path(__file__).parent / "data" / "ner_testset.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 100
    assert any(not r["entities"] for r in rows)            # ada contoh negatif
    by_text = {r["text"]: r for r in rows}
    for r in rows:
        for e in r["entities"]:
            assert e["text"] in r["text"]                  # span benar-benar ada di kalimat
    oracle = evaluate(lambda t: {"entities": by_text[t]["entities"], "confidence": 1.0}, rows)
    assert oracle["f1"] == 1.0 and oracle["char_f1"] == 1.0 and oracle["unaligned_entities"] == 0


def test_collect_records_for_error_analysis():
    r = evaluate(fake_predict, SAMPLES, collect=True)
    assert len(r["records"]) == 3
    assert [x["match"] for x in r["records"]] == [True, False, False]
    assert r["records"][1]["gold"] == [["TIME", "20 detik lagi"]]
    assert r["records"][1]["pred"] == [["TIME", "20 detik"]]
