import os
import telebot
import requests

# =========================
# 1️⃣ قراءة التوكن من متغير البيئة
# =========================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in Railway Variables")

bot = telebot.TeleBot(TOKEN)

print("✅ BOT STARTED SUCCESSFULLY")

# =========================
# 2️⃣ أمر /start
# =========================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🚀 البوت شغال يا فراس!")

# =========================
# 3️⃣ أمر /price (مثال سعر بيتكوين)
# =========================
@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            bot.reply_to(message, "⚠️ خطأ في جلب البيانات من Binance")
            return

        data = response.json()

        if not data or "price" not in data:
            bot.reply_to(message, "⚠️ البيانات غير متوفرة حالياً")
            return

        price = data["price"]
        bot.reply_to(message, f"💰 سعر BTC الحالي: {price} USDT")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")

# =========================
# 4️⃣ تشغيل البوت
# =========================
bot.infinity_polling()
