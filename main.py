import os
import logging
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from g4f.client import Client
import base64
from io import BytesIO

# --- 1. RENDER UCHUN "UYG'OQ TUTUVCHI" SERVER (FLASK) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7 with Vision & Image Generation!"

def run_web():
    # Render avtomatik 10000 portni kutadi
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web, daemon=True).start()

# --- 2. SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHANNEL_ID = "@oripov_live"
ADMIN_ID = 5087939268 # Sizning ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client()

# Foydalanuvchilar ro'yxati (Statistika uchun)
users_list = set()

# Dasturchi ko'rsatmasi (System prompt)
SYSTEM_PROMPT = "Sen dasturchilarga yordam beradigan botman. Javoblaringda kod qismlarini har doim ``` o'ramiga olib, dasturlash tilini ko'rsatib yoz. Savolga aniq va qisqa dasturchi tili bilan javob ber."

# --- 3. YORDAMCHI FUNKSIYALAR ---
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Kanal tekshirishda xato: {e}")
        return False

# --- 4. BUYRUQLAR ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    users_list.add(message.from_user.id)
    
    if await check_sub(message.from_user.id):
        await message.answer(f"Salom {message.from_user.first_name}! 🚀 Dasturchilar uchun maxsus AI botga xush kelibsiz. \n\nMen nima qila olaman:\n✅ Savollaringizga dasturchi sifatida javob beraman.\n✅ Rasmdagi kod xatosini topaman.\n✅ /image buyrug'i bilan rasm yasayman.")
    else:
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga a'zo bo'lish ➕", url="[https://t.me/oripov_live](https://t.me/oripov_live)")],
            [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")]
        ])
        await message.answer("Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=btn)

@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("Rahmat! Endi foydalanishingiz mumkin. 😊")
    else:
        await call.answer("Siz hali a'zo bo'lmadingiz! ❌", show_alert=True)

@dp.message(Command("stat"))
async def show_stat(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        count = len(users_list)
        await message.answer(f"📊 Botingizdan hozirgacha {count} kishi foydalandi.")
    else:
        await message.answer("Siz admin emassiz! ❌")

# --- 5. RASM YASASH FUNKSIYASI ---
@dp.message(Command("image"))
async def generate_image(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("Avval kanalga a'zo bo'ling!")
        return

    # /image buyrug'idan keyingi matnni olish
    prompt = message.text.replace("/image", "").strip()
    if not prompt:
        await message.answer("Rasm yasash uchun tasvir yozing. Masalan: `/image neon lit keyboard`", parse_mode="Markdown")
        return

    wait_msg = await message.answer("Rasm yasalmoqda... 🎨✨")
    
    try:
        # G4F orqali rasm yasash (DALL-E modelidan foydalanadi)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
        )
        image_url = response.data[0].url
        await wait_msg.delete()
        await bot.send_photo(chat_id=message.chat.id, photo=image_url, caption=f"Tasvir: {prompt}")
    except Exception as e:
        logging.error(f"Rasm yasashda xato: {e}")
        await wait_msg.edit_text("Hozirda rasm yasash xizmati band. Birozdan so'ng qayta urinib ko'ring.")

# --- 6. RASM TAHLIL QILISH FUNKSIYASI (VISION) ---
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("Avval kanalga a'zo bo'ling!")
        return

    wait_msg = await message.answer("Rasmni tahlil qilyapman, kuting... 👁️🧠")
    
    try:
        # Rasmni yuklab olish
        photo = await bot.get_file(message.photo[-1].file_id)
        photo_bytes = BytesIO()
        await bot.download_file(photo.file_path, destination=photo_bytes)
        photo_bytes.seek(0)
        
        # Rasmni base64 formatiga o'tkazish
        base64_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
        
        # GPT-4 Vision orqali tahlil qilish
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sen dasturchi 'ko'zisan'. Rasmdagi kodni o'qi, agar xato bo'lsa, xatoni topib, to'g'irlab ber. Agar kod bo'lmasa, rasmni dasturchi nuqtai nazaridan tasvirlab ber. Har doim kod bloklarini ishlat."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Bu rasmdagi kodda xato bormi?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
        )
        answer = response.choices[0].message.content
        await wait_msg.edit_text(answer)
    except Exception as e:
        logging.error(f"Vision xatosi: {e}")
        await wait_msg.edit_text("Hozirda rasmni tahlil qilish imkonsiz. Kodni matn ko'rinishida yuborib ko'ring.")

# --- 7. MATNLI SUHBAT FUNKSIYASI ---
@dp.message(F.text)
async def handle_ai_query(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("Avval kanalga a'zo bo'ling!")
        return

    wait_msg = await message.answer("Javob yuborilmoqda... 🧠⚡️")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
        )
        answer = response.choices[0].message.content
        await wait_msg.edit_text(answer)
    except Exception as e:
        logging.error(f"Xato: {e}")
        await wait_msg.edit_text("Hozirda AI band. Bir ozdan so'ng qayta urinib ko'ring.")

# --- 8. ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print(">>> Dasturchi AI (GPT-4 + Vision) bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())