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

# --- 1. RENDER SERVER (BOTNI O'CHIB QOLMASLIGI UCHUN) ---
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Universal Bot is Live!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web, daemon=True).start()

# --- 2. SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@website_yaratish_xizmati"
ADMIN_ID = 5087939268 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Client()

# --- 3. OBUNA TEKSHIRISH ---
async def check_sub(user_id):
    if user_id == ADMIN_ID: 
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Subscription Error: {e}")
        return False

# --- 4. START BUYRUG'I (SHAXSIYLASHTIRILGAN) ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    name = message.from_user.first_name
    if await check_sub(message.from_user.id):
        await message.answer(
            f"Salom {name}! ✨ Sizning Universal AI yordamchingiz tayyor.\n\n"
            "Mening imkoniyatlarim:\n"
            "💬 **AI Suhbat:** Har qanday savolga javob beraman.\n"
            "🎨 **Rasm Yasash:** /image buyrug'i bilan rasm chizaman.\n"
            "👁️ **Vision:** Kod skrinshotini yuborsangiz, xatosini topaman.\n"
            "💻 **Dasturlash:** Kodlarni tayyor formatda beraman."
        )
    else:
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga a'zo bo'lish ➕", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check")]
        ])
        await message.answer(f"Kechirasiz {name}, botdan foydalanish uchun kanalimizga a'zo bo'lishingiz kerak.", reply_markup=btn)

@dp.callback_query(F.data == "check")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.edit_text("Rahmat! Endi barcha imkoniyatlar ochildi. 😊")
    else:
        await call.answer("Siz hali kanalga a'zo emassiz! ❌", show_alert=True)

# --- 5. RASM YASASH (IMAGE GENERATION) ---
# --- 5. RASM YASASH (IMAGE GENERATION - YANGILANGAN) ---
@dp.message(Command("image"))
async def image_gen(message: types.Message):
    if not await check_sub(message.from_user.id): 
        return
    
    prompt = message.text.replace("/image", "").strip()
    if not prompt:
        await message.answer("Rasm yasash uchun tasvirlab bering. Masalan: `/image modern coding room`.")
        return

    m = await message.answer("Rasm chizilyapti... 🎨✨")
    try:
        # Modelni 'flux'dan 'bing'ga almashtirdik, bu ancha barqaror
        response = client.images.generate(model="bing", prompt=prompt) 
        await bot.send_photo(message.chat.id, photo=response.data[0].url, caption=f"Sizning so'rovingiz: {prompt}")
        await m.delete()
    except Exception as e:
        logging.error(f"Image Error: {e}")
        # Agar bing ham xato bersa, google modelini sinab ko'radi
        try:
            response = client.images.generate(model="google", prompt=prompt)
            await bot.send_photo(message.chat.id, photo=response.data[0].url, caption=f"Tasvir (Google AI): {prompt}")
            await m.delete()
        except:
            await m.edit_text("Hozir rasm yasash xizmati band. Birozdan so'ng qayta urinib ko'ring.")

# --- 6. RASM TAHLILI (VISION - XATOLARNI TOPISH) ---
@dp.message(F.photo)
async def vision_handler(message: types.Message):
    if not await check_sub(message.from_user.id): return

    m = await message.answer("Rasmni tahlil qilyapman... 👁️")
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, destination=file_bytes)
        img_b64 = base64.b64encode(file_bytes.getvalue()).decode()

        response = client.chat.completions.create(
            model="gpt-4o", # Vision uchun eng yaxshisi
            messages=[{
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Bu rasmdagi kodda xato bormi? Bo'lsa, xatoni tushuntir va to'g'ri kodni yozib ber."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }]
        )
        await m.edit_text(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Vision Error: {e}")
        await m.edit_text("Rasmdagi kodni o'qib bo'lmadi. Iltimos, sifatliroq rasm yuboring.")

# --- 7. UNIVERSAL AI SUHBAT (GPT-4) ---
@dp.message(F.text)
async def chat_handler(message: types.Message):
    if not await check_sub(message.from_user.id): return

    m = await message.answer("O'ylayapman... 🧠")
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sen aqlli dasturchi AI yordamchisan. Har doim kod bloklarini ishlat."},
                {"role": "user", "content": message.text}
            ]
        )
        await m.edit_text(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Chat Error: {e}")
        await m.edit_text("Hozir AI biroz band. Birozdan keyin urinib ko'ring.")

# --- 8. ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())