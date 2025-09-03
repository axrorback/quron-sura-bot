import asyncio
import logging
import math
import os
import subprocess

import aiohttp
import aiofiles

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, FSInputFile,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from db import init_db, add_to_library, remove_from_library, get_library
from quron_data import SURAS


# --- Audio split (ffmpeg) ---
def split_audio_ffmpeg(input_file: str, chunk_duration: int = 600) -> list[str]:
    output_files = []

    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", input_file
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip())
    total_chunks = math.ceil(duration / chunk_duration)

    base, ext = os.path.splitext(input_file)
    for i in range(total_chunks):
        start = i * chunk_duration
        out_file = f"{base}_part{i + 1}{ext}"
        cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-ss", str(start),
            "-t", str(chunk_duration),
            "-c", "copy", out_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        output_files.append(out_file)

    return output_files


# --- BOT SETUP ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN") or "TOKEN"

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

MIN_SURA, MAX_SURA = 1, 114


# --- Downloader ---
async def download_sura(sura_number: int, edition="ar.alafasy", bitrate="128"):
    url = f"https://cdn.islamic.network/quran/audio-surah/{bitrate}/{edition}/{sura_number}.mp3"
    save_path = f"data/suras/{sura_number}.mp3"

    if os.path.exists(save_path):
        yield save_path, 100
        return

    os.makedirs("data/suras", exist_ok=True)

    timeout = aiohttp.ClientTimeout(total=300)  # ⏳ 5 daqiqa timeout

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0

            async with aiofiles.open(save_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    progress = int(downloaded / total * 100)
                    yield save_path, progress


# --- Kutubxona tugmasi ---
def build_library_kb(user_id: int, sura_number: int) -> InlineKeyboardMarkup:
    library = get_library(user_id)
    if sura_number in library:
        btn = InlineKeyboardButton(
            text="➖ Kutubxonadan o‘chirish",
            callback_data=f"lib:del:{sura_number}"
        )
    else:
        btn = InlineKeyboardButton(
            text="➕ Kutubxonaga qo‘shish",
            callback_data=f"lib:add:{sura_number}"
        )
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


# --- Start ---
@dp.message(F.text == "/start")
async def start_cmd(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📚 Kutubxonam")]],
        resize_keyboard=True
    )
    text = (
        "🤲 Assalomu alaykum!\n\n"
        "Bu bot <b>Qur’on suralarini</b> tinglash uchun mo‘ljallangan.\n"
        "🎧 Manba: https://cdn.islamic.network\n\n"
        "⚠️ Bot faqat ilm olish va tinglash maqsadida ishlatiladi.\n\n"
        "Sura raqamini yuboring yoki /help buyrug‘ini bosing."
    )
    await message.answer(text, reply_markup=kb)


# --- Help ---
@dp.message(F.text == "/help")
async def help_cmd(message: Message):
    text = "📖 Qur’on suralari ro‘yxati:\n\n"
    for num, name in SURAS.items():
        text += f"{num}. {name}\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tushundim, rahmat", callback_data="help_ok")]
        ]
    )
    await message.answer(text, reply_markup=kb)


# --- Kutubxona ---
@dp.message(F.text == "📚 Kutubxonam")
async def my_library(message: Message):
    library = get_library(message.from_user.id)
    if not library:
        await message.answer("📚 Sizning kutubxonangiz bo‘sh. Avval sura qo‘shib ko‘ring.")
        return

    text = "📚 Sizning kutubxonangiz:\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for s in library:
        sura_name = SURAS.get(s, "Noma’lum sura")
        text += f"{s}. {sura_name}\n"
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"▶️ {sura_name}", callback_data=f"lib:play:{s}")
        ])

    await message.answer(text, reply_markup=kb)


# --- Callback: Kutubxonadan sura olish ---
@dp.callback_query(F.data.startswith("lib:play:"))
async def play_from_library(call: CallbackQuery):
    sura_number = int(call.data.split(":")[2])
    await send_sura(call.message, call.from_user.id, sura_number, from_library=True)
    await call.answer()

# --- Sura yuborish funksiyasi ---
async def send_sura(message: Message, user_id: int, sura_number: int, from_library=False):
    if not (MIN_SURA <= sura_number <= MAX_SURA):
        await message.answer("❗️ Sura raqami 1 dan 114 gacha bo‘lishi kerak.")
        return

    sura_name = SURAS.get(sura_number, f"Sura {sura_number}")

    status_msg = None
    save_path = None
    milestones = {0: False, 50: False, 100: False}  # belgilangan nuqtalar

    async for path, progress in download_sura(sura_number):
        save_path = path

        # 0%
        if progress == 0 and not milestones[0]:
            status_msg = await message.answer(f"⏳ {sura_number}. {sura_name} yuklab olish boshlandi...")
            milestones[0] = True

        # 50%
        elif progress >= 50 and not milestones[50]:
            if status_msg:
                try:
                    await status_msg.edit_text(f"🔄 {sura_number}. {sura_name} yarimga yetdi...")
                except TelegramBadRequest:
                    pass
            milestones[50] = True

        # 100%
        elif progress >= 100 and not milestones[100]:
            if status_msg:
                try:
                    await status_msg.edit_text(f"✅ {sura_number}. {sura_name} to‘liq yuklab olindi.")
                except TelegramBadRequest:
                    pass
            milestones[100] = True
            break  # yuklab olish tugadi

    if not save_path:
        await message.answer("❌ Yuklab olishda muammo yuz berdi.")
        return


    # Bo‘laklash
    parts = split_audio_ffmpeg(save_path, chunk_duration=600)
    caption = f"🎧 <b>{sura_number}. {sura_name}</b>\nManba: cdn.islamic.network"

    kb = build_library_kb(user_id, sura_number)

    for idx, part in enumerate(parts, start=1):
        file = FSInputFile(part, filename=f"{sura_number:03d}-{sura_name}-part{idx}.mp3")
        part_caption = caption if idx == 1 else f"{sura_number}. {sura_name} (qism {idx})"
        await message.answer_audio(
            audio=file,
            caption=part_caption,
            reply_markup=kb
        )
    await message.answer(f"✅ {sura_name} to‘liq yuklab olindi!")

    for part in parts:
        if part != save_path:
            os.remove(part)



# --- User raqam yuborganda ---
@dp.message(F.text.regexp(r"^\d{1,3}$"))
async def handle_sura_request(message: Message):
    try:
        sura_number = int(message.text.strip())
    except ValueError:
        await message.answer("❗️ Iltimos, sura raqamini yuboring (1–114).")
        return

    await send_sura(message, message.from_user.id, sura_number)


# --- Kutubxona qo‘shish/olib tashlash ---
@dp.callback_query(F.data.startswith("lib:"))
async def library_callback(call: CallbackQuery):
    action, subaction, sura_number = call.data.split(":")
    if subaction in ["add", "del"]:
        sura_number = int(sura_number)
        if subaction == "add":
            add_to_library(call.from_user.id, sura_number)
            await call.answer("✅ Kutubxonaga qo‘shildi")
        elif subaction == "del":
            remove_from_library(call.from_user.id, sura_number)
            await call.answer("❌ Kutubxonadan o‘chirildi")

        kb = build_library_kb(call.from_user.id, sura_number)
        try:
            await call.message.edit_reply_markup(reply_markup=kb)
        except TelegramBadRequest:
            pass


# --- Callback: "Tushundim, rahmat" ---
@dp.callback_query(F.data == "help_ok")
async def help_ok_handler(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("✅ Endi sura raqamini yuboring yoki /help dan foydalaning.")
    await callback.answer()


# --- Run bot ---
async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
