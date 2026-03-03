import os
import telebot
import requests
import threading
import time

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

SYMBOLS = ["SOLUSDT","ETHUSDT","OPUSDT","NEARUSDT","ARBUSDT","AVAXUSDT","LINKUSDT","XRPUSDT"]

CHAT_ID = None


def get_klines(symbol, interval, limit=50):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=10)
    return r.json()


def ema(values, period):
    k = 2/(period+1)
    ema_values = [values[0]]
    for price in values[1:]:
        ema_values.append(price*k + ema_values[-1]*(1-k))
    return ema_values


def analyze(symbol):
    try:
        data1h = get_klines(symbol,"1h",60)
        closes1h = [float(x[4]) for x in data1h]

        ema20 = ema(closes1h,20)
        ema50 = ema(closes1h,50)

        if closes1h[-1] < ema50[-1]:
            return None
        if ema20[-1] < ema50[-1]:
            return None

        data15 = get_klines(symbol,"15m",60)
        highs = [float(x[2]) for x in data15]
        lows = [float(x[3]) for x in data15]
        closes = [float(x[4]) for x in data15]
        volumes = [float(x[5]) for x in data15]

        recent_high = max(highs[-21:-1])
        last_close = closes[-1]

        if last_close <= recent_high:
            return None

        volume_avg = sum(volumes[-21:-1]) / 20
        if volumes[-1] < volume_avg:
            return None

        swing_low = min(lows[-21:-1])
        wave = last_close - swing_low

        if wave / last_close < 0.02:
            return None

        tp2 = last_close + wave
        tp3 = last_close + (wave * 1.272)
        sl = swing_low * 0.995

        return f"""
🚀 فرصة – {symbol}

الدخول: {round(last_close,4)}
TP2: {round(tp2,4)}
TP3: {round(tp3,4)}
SL: {round(sl,4)}
قوة الثقة: 70%
"""

    except:
        return None


@bot.message_handler(commands=['start'])
def start_message(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    bot.reply_to(message,"🚀 النظام يعمل ويفحص كل 5 دقائق")


def scanner():
    global CHAT_ID
    while True:
        try:
            if CHAT_ID:
                for symbol in SYMBOLS:
                    result = analyze(symbol)
                    if result:
                        bot.send_message(CHAT_ID,result)
        except:
            pass
        time.sleep(300)


def hourly_ping():
    global CHAT_ID
    while True:
        try:
            if CHAT_ID:
                bot.send_message(CHAT_ID,"✅ النظام يعمل بشكل طبيعي")
        except:
            pass
        time.sleep(3600)


threading.Thread(target=scanner,daemon=True).start()
threading.Thread(target=hourly_ping,daemon=True).start()

bot.remove_webhook()
time.sleep(1)
bot.infinity_polling(skip_pending=True)
