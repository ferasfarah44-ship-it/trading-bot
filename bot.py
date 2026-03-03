import os
import telebot
import requests
import threading
import time

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")

bot = telebot.TeleBot(TOKEN)
print("✅ BOT STARTED")

CHAT_ID = None


# =========================
# START
# =========================
@bot.message_handler(commands=['start'])
def start_message(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    bot.reply_to(message, "🚀 البوت شغال يا فراس!")


# =========================
# جلب السعر من Binance مع حماية
# =========================
def get_binance_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=10)

    if r.status_code != 200:
        return None

    data = r.json()

    if "price" not in data:
        return None

    return float(data["price"])


# =========================
# Fallback من CoinGecko
# =========================
def get_backup_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    r = requests.get(url, timeout=10)
    data = r.json()
    return float(data["bitcoin"]["usd"])


# =========================
# أمر /price
# =========================
@bot.message_handler(commands=['price'])
def price_command(message):
    try:
        price = get_binance_price()

        if price:
            bot.reply_to(message, f"💰 سعر BTC الحالي: {price} USDT")
        else:
            backup = get_backup_price()
            bot.reply_to(message, f"⚠️ Binance غير متاح\n💰 السعر البديل: {backup} USD")

    except Exception as e:
        bot.reply_to(message, "⚠️ خطأ في جلب البيانات")


# =========================
# رسالة كل ساعة
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
# تشغيل نظيف بدون 409
# =========================
bot.remove_webhook()
time.sleep(1)
bot.infinity_polling(skip_pending=True)
