import os
import logging
import asyncio
import threading
import base64
from io import BytesIO
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from g4f.client import Client

# --- SERVERNI UYGOQ TUTISH (FLASK) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is live!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web, daemon=True).start()

# --- SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@oripov_live"
ADMIN_ID = 5087939268 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client()

# --- OBUNA TEKSHIRISH (TUATILGAN VARIANT) ---
async def check_sub(user_id):
    if user_id == ADMIN_ID: return True # Sizga ruxsat
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Obuna xatosi: {e}")
        return False

# --- BUYRUQLAR ---
@dp.message(Command("start"))
async def start(message: types.Message):
    if await check_sub(message.from_user.id):
        await message.answer("Salom! Men tayyorman. 🚀\n\n1. Savol yuboring.\n2. /image buyrug'i bilan rasm yasang.\n3. Rasm (kod skrinshoti) yuborsangiz, xatosini topaman.")
    else:
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check")]
        ])
        await message.answer("Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=btn)

# --- RASM YASASH (/image) ---
@dp.message(Command("image"))
async def make_image(message: types.Message):
    if not await check_sub(message.from_user.id): return
    
    prompt = message.text.replace("/image", "").strip()
    if not prompt:
        await message.answer("Rasm uchun tasvir yozing. Masalan: `/image kod yozayotgan robot`")
        return

    m = await message.answer("Rasm chizilyapti... 🎨")
    try:
        response = client.images.generate(model="dall-e-3", prompt=prompt)
        await bot.send_photo(message.chat.id, photo=response.data[0].url, caption=f"Tayyor: {prompt}")
        await m.delete()
    except:
        await m.edit_text("Hozir rasm yasab bo'lmadi, qayta urinib ko'ring.")

# --- RASM TAHLIL QILISH (VISION) ---
@dp.message(F.photo)
async def analyze_photo(message: types.Message):
    if not await check_sub(message.from_user.id): return

    m = await message.answer("Rasmni ko'ryapman... 👁️")
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, destination=file_bytes)
        img_b64 = base64.b64encode(file_bytes.getvalue()).decode()

        response = client.chat.completions.create(
            model="gpt-4o", # Vision uchun eng yaxshisi
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "Bu rasmdagi kodda xato bormi? Bo'lsa tuzatib ber."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]}]
        )
        await m.edit_text(response.choices[0].message.content)
    except:
        await m.edit_text("Rasmdagi kodni o'qib bo'lmadi.")

# --- ODDIY SUHBAT ---
@dp.message(F.text)
async def chat(message: types.Message):
    if not await check_sub(message.from_user.id): return
    m = await message.answer("O'ylayapman... 🧠")
    try:
        res = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sen dasturchisan. Kodlarni har doim ``` ichida yoz."},
                {"role": "user", "content": message.text}
            ]
        )
        await m.edit_text(res.choices[0].message.content)
    except:
        await m.edit_text("AI hozir javob bera olmaydi.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())