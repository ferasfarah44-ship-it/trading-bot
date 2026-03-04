import os
import requests
import telebot
import time

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

SYMBOLS = [
"SOLUSDT","ETHUSDT","LINKUSDT","NEARUSDT",
"OPUSDT","ARBUSDT","BNBUSDT","AVAXUSDT",
"ADAUSDT","SUIUSDT","DOGEUSDT"
]

CHAT_ID = None
last_heartbeat = time.time()


def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=30"
    r = requests.get(url,timeout=10)
    return r.json()


def analyze(symbol):

    data = get_klines(symbol)

    closes = [float(x[4]) for x in data]
    highs = [float(x[2]) for x in data]
    lows = [float(x[3]) for x in data]

    price = closes[-1]

    # breakout
    breakout = price > max(highs[-20:])

    # momentum
    momentum = (price - closes[-5]) / closes[-5] > 0.015

    # compression
    compression = (max(highs[-10:]) - min(lows[-10:])) / price < 0.01

    reason = None

    if breakout:
        reason = "Breakout"

    if momentum:
        reason = "Momentum"

    if compression:
        reason = "Compression"

    if reason:
        return f"""
🚨 فرصة حركة

العملة: {symbol}
السعر: {round(price,4)}

السبب:
{reason}
"""
    return None


@bot.message_handler(commands=['start'])
def start(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    bot.reply_to(message,"🚀 البوت بدأ تحليل السوق")


def scanner():

    global last_heartbeat

    while True:

        try:

            if CHAT_ID:

                for symbol in SYMBOLS:

                    signal = analyze(symbol)

                    if signal:
                        bot.send_message(CHAT_ID,signal)

                # رسالة كل ساعة
                if time.time() - last_heartbeat > 3600:
                    bot.send_message(CHAT_ID,"✅ البوت يعمل بشكل طبيعي")
                    last_heartbeat = time.time()

        except Exception as e:
            print("error:",e)

        time.sleep(60)


def run():

    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(5)


import threading
threading.Thread(target=scanner).start()

run()
