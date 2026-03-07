import os
import logging
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from g4f.client import Client

# --- 1. RENDER UCHUN "UYG'OQ TUTUVCHI" SERVER (FLASK) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    # Render 10000 portini avtomatik qidiradi
    app.run(host="0.0.0.0", port=10000)

# Serverni alohida oqimda (thread) ishga tushirish
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
    # Foydalanuvchini statistikaga qo'shish
    users_list.add(message.from_user.id)
    
    if await check_sub(message.from_user.id):
        await message.answer(f"Salom {message.from_user.first_name}! 🚀 Senga qanday yordam bera olaman? Tushunmayotgan savolingiz bo'lsa yozing.")
    else:
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga a'zo bo'lish ➕", url="https://t.me/oripov_live")],
            [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")]
        ])
        await message.answer("Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=btn)

@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("Rahmat! Endi savol yuborishingiz mumkin. 😊")
    else:
        await call.answer("Siz hali a'zo bo'lmadingiz! ❌", show_alert=True)

@dp.message(Command("stat"))
async def show_stat(message: types.Message):
    # Faqat admin uchun statistika
    if message.from_user.id == ADMIN_ID:
        count = len(users_list)
        await message.answer(f"📊 Botingizdan hozirgacha {count} kishi foydalandi.")
    else:
        await message.answer("Siz admin emassiz! ❌")

@dp.message(F.text)
async def handle_ai_query(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("Avval kanalga a'zo bo'ling!")
        return

    wait_msg = await message.answer("Javob yuborilmoqda... 🧠⚡️")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": message.text}],
        )
        answer = response.choices[0].message.content
        await wait_msg.edit_text(answer)
    except Exception as e:
        logging.error(f"Xato: {e}")
        await wait_msg.edit_text("Hozirda AI band. Bir ozdan so'ng qayta urinib ko'ring.")

# --- 5. ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print(">>> KodBilim AI (GPT-4) bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())