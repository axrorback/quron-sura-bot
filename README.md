# 📖 Qur'on Suralari Bot

Bu loyiha — **aiogram 3.x** yordamida yozilgan **Telegram bot**, foydalanuvchilarga Qur’on suralarini tinglash, saqlash va boshqarish imkoniyatini beradi.

🔓 **Loyiha to‘liq open-source** — hamma foydalanishi, o‘zgartirishi va ulashishi mumkin.

---

## ✨ Xususiyatlari

* 🎧 **Qur’on suralarini yuklab olish va tinglash**
* 📚 **Kutubxonaga qo‘shish / o‘chirish**
* ⏳ **Yuklab olish progressi** (0%, 50%, 100%) ko‘rsatiladi
* 🔄 **Audio fayl bo‘laklarga ajratiladi** (`ffmpeg` yordamida)
* 🗑 **Botni tozalash** tugmasi — chatni va kutubxonani tozalash

---

## 🚀 O‘rnatish

### 1. Repozitoriyani clone qilish

```bash
git clone https://github.com/axrorback/quron-sura-bot.git
cd quron-bot
```

### 2. Virtual environment yaratish

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/MacOS
type .venv\Scripts\activate # Windows
```

### 3. Kerakli kutubxonalarni o‘rnatish

```bash
pip install -r requirements.txt
```

### 4. `.env` fayl yaratish

```
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

### 5. `ffmpeg` o‘rnatish

* **Linux/MacOS**:

```bash
sudo apt install ffmpeg   # Debian/Ubuntu
brew install ffmpeg       # MacOS (Homebrew)
```

* **Windows**: [ffmpeg.org](https://ffmpeg.org/download.html) saytidan yuklab oling va PATH ga qo‘shing.

---

## ▶️ Ishga tushirish

```bash
python main.py
```

---

## 📂 Loyihaning tuzilishi

```
quron-bot/
├── main.py           # Botning asosiy kodi
├── db.py             # SQLite DB funksiyalari
├── quron_data.py     # Suralar ro‘yxati
├── requirements.txt  # Kerakli kutubxonalar
└── .env              # Tokenni saqlash
```

---

## 📸 Bot imkoniyatlari

* `/start` — Botni ishga tushirish
* `/help` — Suralar ro‘yxatini ko‘rish
* **Raqam yuborish (1–114)** — Sura yuklab olinadi va yuboriladi
* **📚 Kutubxonam** — saqlangan suralarni ko‘rish
* **🗑 Botni tozalash** — chat va kutubxonani tozalash

---

## 🛠 Texnologiyalar

* [Python 3.10+](https://www.python.org/)
* [Aiogram 3.x](https://docs.aiogram.dev/)
* [Aiohttp](https://docs.aiohttp.org/)
* [SQLite3](https://www.sqlite.org/)
* [FFmpeg](https://ffmpeg.org/)

---

## 🤲 Eslatma

⚠️ Ushbu bot faqat **ilm olish va tinglash maqsadida** ishlatiladi. Qur’onni nojoiz ishlatishdan saqlaning.

---

## 📜 Litsenziya

MIT License — bemalol foydalanishingiz, o‘zgartirishingiz va ulashishingiz mumkin.

🌍 Ushbu loyiha **open-source** bo‘lib, hamjamiyat tomonidan rivojlantirilishi mumkin.
