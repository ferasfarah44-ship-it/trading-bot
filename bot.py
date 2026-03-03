import os
import telebot
import requests
import threading
import time

# =========================
# قراءة التوكن
# =========================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")

bot = telebot.TeleBot(TOKEN)

print("✅ BOT STARTED SUCCESSFULLY")

CHAT_ID = None

# =========================
# عند /start
# =========================
@bot.message_handler(commands=['start'])
def start_message(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    bot.reply_to(message, "🚀 البوت شغال يا فراس!")

# =========================
# جلب السعر من Binance
# =========================
@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            bot.reply_to(message, f"⚠️ Binance Error: {response.status_code}")
            return

        data = response.json()

        if "price" not in data:
            bot.reply_to(message, "⚠️ لم يتم العثور على السعر")
            return

        price = float(data["price"])
        bot.reply_to(message, f"💰 سعر BTC الحالي: {price} USDT")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")

# =========================
# رسالة كل ساعة للتأكد
# =========================
def hourly_check():
    global CHAT_ID
    while True:
        if CHAT_ID:
            try:
                bot.send_message(CHAT_ID, "✅ البوت يعمل بشكل طبيعي")
            except:
                pass
        time.sleep(3600)

threading.Thread(target=hourly_check, daemon=True).start()

# =========================
# تشغيل البوت (حل مشكلة 409)
# =========================
bot.remove_webhook()
time.sleep(1)
bot.infinity_polling(skip_pending=True)
