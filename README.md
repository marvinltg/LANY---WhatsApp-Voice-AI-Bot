# LANY - WhatsApp Voice AI Bot

LANY adalah asisten suara cerdas (Voice AI) yang terintegrasi langsung dengan WhatsApp. Proyek ini mengotomatiskan interaksi panggilan masuk di WhatsApp melalui sistem *Text-to-Speech* (TTS) dan *Speech-to-Text* (STT) real-time, ditenagai oleh *Large Language Model* (LLM) untuk menghasilkan percakapan dua arah yang natural.

## Fitur Utama

- **Integrasi Panggilan WhatsApp**: Menerima dan merespons panggilan WhatsApp secara otomatis menggunakan browser automation (Playwright).
- **Pemrosesan Audio Real-Time**: Mendukung *Voice Activity Detection* (VAD) untuk deteksi percakapan secara akurat.
- **Ditenagai oleh AI**: Memanfaatkan Groq Engine untuk pemrosesan bahasa yang sangat cepat, serta integrasi Edge-TTS/ElevenLabs untuk output suara.
- **Manajemen Sesi Otomatis**: Menangani status panggilan, buffering audio, dan kalibrasi noise secara cerdas.

## Persyaratan Sistem

- Python 3.8 atau lebih baru.
- Virtual Audio Cable (seperti VB-Cable atau Voicemeeter) untuk perutean audio I/O secara virtual.
- Akun WhatsApp yang aktif.

## Instalasi

1. Clone repositori ini atau buka direktori proyek.
2. Buat dan aktifkan *virtual environment* (sangat direkomendasikan):
   ```bash
   python -m venv venv
   # Di Windows:
   venv\Scripts\activate
   # Di Linux/Mac:
   source venv/bin/activate
   ```
3. Instal semua dependensi yang diperlukan:
   ```bash
   pip install -r requirements.txt
   ```
4. Instal browser untuk Playwright:
   ```bash
   playwright install chromium
   ```
5. Konfigurasikan file `.env` dengan kredensial API (seperti Groq API Key) dan nama perangkat audio virtual Anda.

## Penggunaan

Untuk menjalankan LANY AI Bot, eksekusi perintah berikut di terminal Anda:

```bash
python main.py
```

Pada saat pertama kali dijalankan, Anda mungkin perlu memindai kode QR untuk masuk ke WhatsApp Web. Setelah masuk, sistem akan siaga dan merespons panggilan masuk secara otomatis.

## Lisensi

Proyek ini dibuat untuk keperluan pengembangan dan otomatisasi AI. Hak cipta milik pengembang.
