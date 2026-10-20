"""
Membangun test set NER baru (tests/data/ner_testset.jsonl).

Setiap kalimat dirakit dari: kerangka kalimat + aktivitas + ekspresi waktu. Karena
rakitan, posisi entitas pasti benar (label dibuat bersamaan dengan teks). Seed
tetap sehingga hasilnya selalu sama. Jalankan: python tools/build_ner_testset.py

Tipe gold (kasar): DATE (besok, hari jumat, minggu depan), TIME (jam 7 pagi, malam),
DURATION (20 detik lagi, setengah jam lagi). Jika label model Anda berbeda, pakai
`--type-map` atau metrik char-level di evaluate_ner.py yang tidak bergantung label.
"""
import json
import random
from pathlib import Path

ACTIVITIES = [
    "rapat tim", "minum obat", "kerja kelompok", "jemput adik", "bayar listrik",
    "telepon ibu", "olahraga", "kirim laporan", "beli galon", "servis motor",
    "belajar python", "ambil paket", "cek email", "masak nasi", "ikut kelas online",
    "ketemu dosen pembimbing", "submit tugas", "siram tanaman", "backup data",
    "latihan presentasi",
]
PREFIXES = ["ingatkan saya", "tolong ingatkan", "reminder", "alarm untuk", "jangan lupa"]

D, T, R = "DATE", "TIME", "DURATION"
EXPRESSIONS = [
    # durasi relatif
    [("20 detik lagi", R)], [("5 menit lagi", R)], [("45 menit lagi", R)],
    [("2 jam lagi", R)], [("setengah jam lagi", R)], [("sejam lagi", R)],
    [("dua puluh menit lagi", R)], [("3 hari lagi", R)], [("1 minggu lagi", R)],
    [("dalam 15 menit", R)], [("dalam 2 jam", R)], [("tiga jam lagi", R)],
    [("10 detik lagi", R)], [("90 menit lagi", R)],
    # tanggal + jam
    [("besok", D), ("jam 7 pagi", T)], [("besok", D), ("jam 06.30", T)],
    [("lusa", D), ("pukul 13.30", T)], [("lusa", D), ("jam 8 malam", T)],
    [("hari jumat", D), ("jam 14.00", T)], [("hari sabtu", D), ("jam 10 pagi", T)],
    [("kamis", D), ("jam setengah 10 pagi", T)], [("selasa", D), ("jam 3 sore", T)],
    [("hari ini", D), ("jam 21.00", T)], [("hari ini", D), ("jam 5 sore", T)],
    [("senin", D), ("jam 8 pagi", T)],
    [("minggu depan", D), ("hari senin", D), ("jam 9 pagi", T)],
    [("jumat", D), ("minggu depan", D), ("jam 13.00", T)],
    [("besok", D), ("pagi", T)], [("besok", D), ("siang", T)],
    [("besok", D), ("malam", T), ("jam 8", T)], [("lusa", D), ("pagi", T)],
    [("rabu", D), ("sore", T)], [("sabtu", D), ("malam", T), ("jam 7", T)],
    [("hari minggu", D), ("jam 8 pagi", T)],
    [("besok", D), ("jam sembilan pagi", T)], [("besok", D), ("jam 2 siang", T)],
    [("kamis", D), ("malam", T)],
    # hanya waktu
    [("jam 3 sore", T)], [("jam sepuluh malam", T)], [("jam 7 kurang 15 menit", T)],
    [("pukul 19.30", T)], [("nanti malam", T)], [("nanti sore", T)],
    [("jam 5 pagi", T)], [("jam setengah 8 malam", T)], [("malam ini", T)],
    [("sore ini", T)], [("jam 12 siang", T)], [("jam 16.45", T)], [("jam 11 malam", T)],
]
NEGATIVES = [
    "tolong catat daftar belanja bulanan", "buatkan catatan rapat tim",
    "ibu sedang memasak nasi goreng", "saya ingin belajar python lebih dalam",
    "kirim laporan ke dosen pembimbing", "beli galon dan gas elpiji",
    "servis motor di bengkel dekat rumah", "apa saja tugas saya",
    "siram tanaman di teras depan", "tambahkan catatan untuk proyek skripsi",
]


def assemble(segments, activity, frame, prefix):
    time_text = " ".join(s for s, _ in segments)
    if frame == 0:
        text = f"{prefix} {activity} {time_text}"
    elif frame == 1:
        text = f"{time_text} {activity}"
    elif frame == 2:
        text = f"{activity} {time_text}"
    else:
        text = f"{prefix} {time_text} untuk {activity}"
    ents = [{"type": t, "text": s} for s, t in segments]
    for e in ents:
        assert e["text"] in text
    return text, ents


def main():
    rng = random.Random(42)
    rows, seen = [], set()

    def push(text, ents):
        key = text.lower()
        if key in seen:
            return False
        seen.add(key)
        rows.append({"text": text, "entities": ents})
        return True

    for _ in range(2):                      # tiap ekspresi dipakai minimal 2 kali
        for seg in EXPRESSIONS:
            while True:
                text, ents = assemble(seg, rng.choice(ACTIVITIES), rng.randrange(4), rng.choice(PREFIXES))
                if rng.random() < 0.15:
                    text = text[0].upper() + text[1:]
                    for e in ents:  # jaga agar teks entitas tetap substring persis dari kalimat
                        if e["text"] not in text:
                            e["text"] = e["text"][0].upper() + e["text"][1:]
                if push(text, ents):
                    break
    for _ in range(15):                     # tambahan acak
        seg = rng.choice(EXPRESSIONS)
        text, ents = assemble(seg, rng.choice(ACTIVITIES), rng.randrange(4), rng.choice(PREFIXES))
        push(text, ents)
    for neg in NEGATIVES:                   # kalimat tanpa ekspresi waktu
        push(neg, [])

    rng.shuffle(rows)
    out = Path(__file__).resolve().parent.parent / "tests" / "data" / "ner_testset.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    pos = sum(1 for r in rows if r["entities"])
    print(f"{len(rows)} kalimat ({pos} berentitas, {len(rows) - pos} negatif) -> {out}")


if __name__ == "__main__":
    main()
