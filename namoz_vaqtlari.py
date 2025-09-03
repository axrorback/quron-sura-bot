import asyncio
import aiohttp
import sqlite3
from datetime import datetime, timedelta, date

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
from dotenv import load_dotenv
load_dotenv() #env bu siz yuklanmaydi esdan chiqmasinda Axrorbek 🥲🥲
API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=str(API_TOKEN))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# === DATABASE ===
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            region TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qazo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            namoz TEXT
        )
    """)
    conn.commit()
    conn.close()

def set_user_region(user_id: int, region: str):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users (user_id, region) VALUES (?, ?)", (user_id, region))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, region FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_qazo(user_id: int, date_: str, namoz: str):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO qazo (user_id, date, namoz) VALUES (?, ?, ?)", (user_id, date_, namoz))
    conn.commit()
    conn.close()

def get_qazo(user_id: int):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT date, namoz FROM qazo WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def clear_qazo(user_id: int):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM qazo WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# === API FUNCTION ===
async def get_pray_times(region: str):
    today = date.today().strftime("%Y-%m-%d")
    url = f"https://namoz-vaqtlari.more-info.uz:444/api/GetDailyPrayTimes/{region}/{today}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data["response"]

# === INLINE KEYBOARDS ===
regions = [
    "Toshkent", "Andijon", "Fargona", "Namangan",
    "Samarqand", "Buxoro", "Navoiy", "Qashqadaryo",
    "Surxondaryo", "Jizzax", "Sirdaryo", "Xorazm",
    "Qoraqalpog‘iston"
]

def regions_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=reg, callback_data=f"region:{reg}")] for reg in regions
    ])
    return kb

def change_region_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Viloyatni o‘zgartirish", callback_data="change_region")]
    ])


# === REMINDERS & QUESTIONS ===
async def remind_before_prayer(user_id: int, namoz: str, vaqti: str):
    await bot.send_message(user_id, f"🕌 {namoz} namoziga tayyorlaning!\nBugun {namoz} vaqti: {vaqti}")

async def ask_after_prayer(user_id: int, namoz: str, date_: str):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ O‘qidim", callback_data=f"done:{date_}:{namoz}")],
        [InlineKeyboardButton(text="❌ Qazo bo‘ldi", callback_data=f"qazo:{date_}:{namoz}")]
    ])
    await bot.send_message(user_id, f"📅 {date_}\nSiz {namoz} namozini o‘qidingizmi?", reply_markup=kb)

@dp.callback_query(F.data.startswith("qazo:"))
async def qazo_handler(callback: CallbackQuery):
    _, date_, namoz = callback.data.split(":")
    add_qazo(callback.from_user.id, date_, namoz)
    await callback.message.edit_text(f"❌ {date_} sanasidagi {namoz} qazo sifatida saqlandi.")

@dp.callback_query(F.data.startswith("done:"))
async def done_handler(callback: CallbackQuery):
    _, date_, namoz = callback.data.split(":")
    await callback.message.edit_text(f"✅ {date_} {namoz} o‘qilgan sifatida belgilandi. Barakalla!")

@dp.message(F.text == "/qazo")
async def show_qazo(message: Message):
    rows = get_qazo(message.from_user.id)
    if not rows:
        await message.answer("🎉 Sizda qazo namoz yo‘q!")
    else:
        text = "📋 Sizda qazo namozlar mavjud:\n\n"
        for d, n in rows:
            text += f"- {d} {n}\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Qazolarni tozalash", callback_data="clear_qazo")]
        ])
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "clear_qazo")
async def clear_qazo_handler(callback: CallbackQuery):
    clear_qazo(callback.from_user.id)
    await callback.message.edit_text("✅ Qazolar tozalandi.")


# === JOBLARNI QO‘SHISH ===
async def schedule_user_jobs():
    users = get_all_users()
    for user_id, region in users:
        try:
            times = await get_pray_times(region)

            today = times["date"]
            namozlar = {
                "Bomdod": times["bomdod"],
                "Peshin": times["peshin"],
                "Asr": times["asr"],
                "Shom": times["shom"],
                "Xufton": times["xufton"]
            }

            for nomi, vaqti in namozlar.items():
                # Namoz vaqtini datetime shaklga o'tkazamiz
                pray_time = datetime.strptime(f"{today} {vaqti}", "%Y-%m-%d %H:%M:%S")

                # 5 daqiqa oldin
                remind_time = pray_time - timedelta(minutes=5)
                if remind_time > datetime.now():
                    scheduler.add_job(remind_before_prayer, "date", run_date=remind_time,
                                      args=[user_id, nomi, vaqti])

                # Namozdan keyin (5 daqiqa keyin)
                ask_time = pray_time + timedelta(minutes=5)
                if ask_time > datetime.now():
                    scheduler.add_job(ask_after_prayer, "date", run_date=ask_time,
                                      args=[user_id, nomi, today])

        except Exception as e:
            print(f"Xato {user_id} uchun job qo‘yishda: {e}")


# === HANDLERS ===
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("Assalomu alaykum! Viloyatingizni tanlang 👇", reply_markup=regions_keyboard())

@dp.callback_query(F.data.startswith("region:"))
async def region_handler(callback: CallbackQuery):
    region = callback.data.split(":")[1]
    set_user_region(callback.from_user.id, region)

    times = await get_pray_times(region)
    text = (
        f"📍 <b>{times['region']}</b> uchun bugungi namoz vaqtlari:\n\n"
        f"🌅 Bomdod: {times['bomdod']}\n"
        f"🕌 Peshin: {times['peshin']}\n"
        f"🌇 Asr: {times['asr']}\n"
        f"🌆 Shom: {times['shom']}\n"
        f"🌙 Xufton: {times['xufton']}\n\n"
        f"📅 Sana: {times['date']}"
    )
    await callback.message.edit_text(text, reply_markup=change_region_keyboard(), parse_mode="HTML")

    # Shu user uchun bugungi joblarni qayta qo‘shamiz
    await schedule_user_jobs()

@dp.callback_query(F.data == "change_region")
async def change_region_handler(callback: CallbackQuery):
    await callback.message.edit_text("Yangi viloyatni tanlang 👇", reply_markup=regions_keyboard())


# === MAIN ===
async def main():
    init_db()
    scheduler.start()

    # Har kuni 00:10 da barcha userlar uchun joblarni qayta qo‘yish
    scheduler.add_job(schedule_user_jobs, "cron", hour=0, minute=10)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
