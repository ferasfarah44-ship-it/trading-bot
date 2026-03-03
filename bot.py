import os
import telebot
import requests
import threading
import time
import pandas as pd

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

SYMBOLS = ["SOLUSDT","ETHUSDT","OPUSDT","NEARUSDT","ARBUSDT","AVAXUSDT","LINKUSDT","XRPUSDT"]

CHAT_ID = None

def get_klines(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url)
    data = r.json()
    df = pd.DataFrame(data)
    df = df.iloc[:,0:6]
    df.columns = ["time","open","high","low","close","volume"]
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

def analyze(symbol):
    df1h = get_klines(symbol,"1h",100)
    df15 = get_klines(symbol,"15m",100)

    df1h["ema20"] = df1h["close"].ewm(span=20).mean()
    df1h["ema50"] = df1h["close"].ewm(span=50).mean()

    # اتجاه
    if df1h["close"].iloc[-1] < df1h["ema50"].iloc[-1]:
        return None

    if df1h["ema20"].iloc[-1] < df1h["ema50"].iloc[-1]:
        return None

    # كسر مقاومة 15m
    recent_high = df15["high"].iloc[-21:-1].max()
    last_close = df15["close"].iloc[-1]

    if last_close <= recent_high:
        return None

    volume_avg = df15["volume"].iloc[-21:-1].mean()
    if df15["volume"].iloc[-1] < volume_avg:
        return None

    swing_low = df15["low"].iloc[-21:-1].min()
    wave = last_close - swing_low

    if wave / last_close < 0.02:
        return None

    tp2 = last_close + wave
    tp3 = last_close + (wave * 1.272)
    sl = swing_low * 0.995

    confidence = 70

    return {
        "symbol": symbol,
        "entry": round(last_close,4),
        "tp2": round(tp2,4),
        "tp3": round(tp3,4),
        "sl": round(sl,4),
        "confidence": confidence
    }

@bot.message_handler(commands=['start'])
def start_message(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    bot.reply_to(message,"🚀 نظام التحليل الاحترافي يعمل")

def scanner():
    global CHAT_ID
    while True:
        if CHAT_ID:
            for symbol in SYMBOLS:
                result = analyze(symbol)
                if result:
                    msg = f"""
🚀 فرصة محتملة – {result['symbol']}

الدخول: {result['entry']}
TP2: {result['tp2']}
TP3: {result['tp3']}
SL: {result['sl']}

قوة الثقة: {result['confidence']}%
"""
                    bot.send_message(CHAT_ID,msg)
        time.sleep(300)

def hourly_ping():
    global CHAT_ID
    while True:
        if CHAT_ID:
            bot.send_message(CHAT_ID,"✅ النظام يعمل ويتم الفحص كل 5 دقائق")
        time.sleep(3600)

threading.Thread(target=scanner,daemon=True).start()
threading.Thread(target=hourly_ping,daemon=True).start()

bot.remove_webhook()
time.sleep(1)
bot.infinity_polling(skip_pending=True)
