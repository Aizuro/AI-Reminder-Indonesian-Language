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
- Confidence score hasil prediksi model
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
├── requirements.txt
├── config.py
├── src
│   ├── __init__.py
│   ├── ner_model.py
│   └── time_normalizer.py
└── README.md

---

## Live Demo

https://huggingface.co/spaces/Aizuro/AI-Reminder-Indonesian-Language

---

## Notes

- Tab browser harus tetap terbuka agar alarm dapat berbunyi


---

## Author

Aizuro (Abdul Azizur Rokhman)
AI / NLP Project – Indonesian Language