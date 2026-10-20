---
title: AI Reminder Indonesian Language
emoji: ⏰
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
---

# ⏰ AI Reminder – Indonesian Language

AI Reminder berbasis Named Entity Recognition (NER) untuk Bahasa Indonesia.
Aplikasi ini memahami perintah bahasa alami dan mengubahnya menjadi pengingat atau alarm otomatis.

Contoh perintah:
- ingatkan saya besok jam 7 pagi rapat
- alarm 20 detik lagi
- makan siang hari ini jam 12.30

---

## Features

- Pemrosesan bahasa alami (Bahasa Indonesia)
- Named Entity Recognition (NER) berbasis **BiLSTM-CRF**
- Normalisasi waktu otomatis (relative & absolute time)
- Countdown real-time
- Alarm otomatis dengan audio
- Confidence score hasil prediksi model (indikator keyakinan model, **bukan** metrik akurasi — lihat Evaluation)
- Ekspor reminder ke kalender (`.ics`) untuk Google Calendar / Outlook
- Ekspresi waktu sehari-hari: "setengah 8", "jam 7 kurang 15", "sepuluh menit lagi", "minggu depan"
- Visualisasi entitas NER
- Debug information
- Voice input (Chrome / Edge)
- Auto-check alarm setiap 1 detik

---

## Model

Model NER di-load langsung dari Hugging Face Model Hub:

https://huggingface.co/Aizuro/indonesian-ner-time_reminder

Tidak menggunakan model lokal di Hugging Face Space.

---

## Tech Stack

- Python
- Gradio (Blocks)
- PyTorch
- Hugging Face Transformers
- Pandas

---

## Project Structure

.
├── app.py
├── evaluate_normalizer.py      # evaluasi end-to-end normalisasi waktu
├── evaluate_ner.py             # evaluasi NER (P/R/F1, latensi, confidence vs kebenaran)
├── requirements.txt
├── requirements-dev.txt
├── tools
│   └── build_ner_testset.py    # pembuat test set NER (seed tetap)
├── src
│   ├── ner_model.py
│   ├── time_normalizer.py
│   ├── ics_export.py
│   └── token_utils.py
├── tests
│   ├── data/normalizer_cases.json     # 118 kasus berlabel manual (dev)
│   ├── data/normalizer_holdout.json   # 42 kasus held-out
│   ├── data/ner_testset.jsonl         # 125 kalimat uji NER (115 berentitas, 10 negatif)
│   └── test_*.py
└── README.md

---

## Live Demo

https://huggingface.co/spaces/Aizuro/AI-Reminder-Indonesian-Language

---

## Evaluation

Sebelumnya project ini hanya menampilkan confidence score. Confidence dihitung dari
rata-rata probabilitas tertinggi semua token (termasuk token `O`), sehingga hanya
menunjukkan keyakinan model, bukan kebenaran hasil. Sekarang tersedia evaluasi nyata.

### 1. Normalisasi waktu (teks → datetime), exact match

Ground truth ditulis manual dengan `now` dibekukan (Senin, 19 Okt 2026 14:00 WIB).

```bash
python evaluate_normalizer.py              # rule-based saja
python evaluate_normalizer.py --with-ner   # pipeline penuh NER → normalizer
python evaluate_normalizer.py --markdown   # tabel untuk README
```

Dev set (118 kasus) — sebelum vs sesudah perbaikan hasil error analysis:

| Kategori | Sebelum | Sesudah |
|---|---|---|
| relative ("5 menit lagi", "setengah jam lagi") | 13/26 (50%) | 26/26 (100%) |
| absolute_clock ("jam 16.00") | 20/20 (100%) | 20/20 (100%) |
| part_of_day ("jam 2 sore") | 22/24 (92%) | 24/24 (100%) |
| weekday_date ("jumat minggu depan") | 18/23 (78%) | 23/23 (100%) |
| colloquial ("setengah 8", "jam sepuluh", "7 kurang 15") | 2/25 (8%) | 25/25 (100%) |
| **Total** | **75/118 (63,6%)** | **118/118 (100%)** |

Karena dev set disusun bersamaan dengan perbaikan, angka 100% bersifat optimistis.
Untuk estimasi yang lebih jujur ada held-out set terpisah (`tests/data/normalizer_holdout.json`)
yang dijalankan sekali sebelum perbaikan lanjutan:

| Held-out | Hasil |
|---|---|
| Frasa umum (typical) | 37/37 (100%) |
| Di luar cakupan (lihat Known limitations) | 0/5 |

### 2. NER (level entitas)

Test set: `tests/data/ner_testset.jsonl` (125 kalimat: 90 TIME, 62 DATE, 31 DURATION,
10 kalimat tanpa ekspresi waktu untuk mengukur false positive). Dirakit dari kerangka
kalimat × aktivitas × ekspresi waktu dengan seed tetap (`tools/build_ner_testset.py`),
sehingga label dan posisi entitas dijamin konsisten. Data ini dibuat terpisah dari data
training dan belum pernah dipakai melatih model.

```bash
python evaluate_ner.py --jsonl tests/data/ner_testset.jsonl
# jika nama label model berbeda dari gold (DATE/TIME/DURATION):
python evaluate_ner.py --jsonl tests/data/ner_testset.jsonl --type-map DATE=DAT,TIME=TIM
# batasi ke tipe tertentu (abaikan entitas lain milik model, mis. aktivitas):
python evaluate_ner.py --jsonl tests/data/ner_testset.jsonl --only-types DATE,TIME,DURATION
```

Melaporkan: precision/recall/F1 *strict* (tipe + teks, micro & per tipe), F1 *level karakter*
(tidak bergantung pada nama label maupun cara model memotong entitas), sentence exact match,
latensi (rata-rata & p95), serta rata-rata confidence untuk kalimat benar vs salah.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

## Known limitations

- Durasi majemuk ("1 jam 30 menit lagi") hanya membaca bagian terakhir.
- Tanggal kalender eksplisit ("tanggal 25 Oktober") belum didukung.
- "seperempat jam lagi", "tengah malam", dan "10 menit sebelum jam 5" belum didukung.
- Jam tanpa penanda pagi/siang/sore/malam dibaca apa adanya (mis. "jam 3" = 03:00).
- Waktu hari ini yang sudah lewat digeser ke besok (kebijakan, bukan bug).

---

## Notes

- Tab browser harus tetap terbuka agar alarm dapat berbunyi


---

## Author

Aizuro (Abdul Azizur Rokhman)
AI / NLP Project – Indonesian Language