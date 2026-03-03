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

# =========================
# حفظ chat_id أول شخص يكتب
# =========================
CHAT_ID = None

@bot.message_handler(commands=['start'])
def start_message(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    bot.reply_to(message, "🚀 البوت شغال يا فراس!")

# =========================
# أمر السعر
# =========================
@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            bot.reply_to(message, "⚠️ خطأ في جلب البيانات")
            return

        data = response.json()
        price = data["bitcoin"]["usd"]

        bot.reply_to(message, f"💰 سعر BTC الحالي: {price} USD")

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
        time.sleep(3600)  # كل ساعة

# تشغيل الثريد
threading.Thread(target=hourly_check, daemon=True).start()

# =========================
# تشغيل البوت
# =========================
bot.infinity_polling()
