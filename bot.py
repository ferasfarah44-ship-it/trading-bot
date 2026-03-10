import requests
import time
import pandas as pd
import numpy as np
import os
from datetime import datetime
import telegram

# قراءة القيم من Environment Variables في Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_TOKEN)

COINS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","ADAUSDT",
    "NEARUSDT","OPUSDT","ARBUSDT","LINAUSDT",
    "BNBUSDT","LINKUSDT","INJUSDT","FETUSDT"
]

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=120"
    data = requests.get(url).json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "c1","c2","c3","c4","c5","c6"
    ])

    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze(df):
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()
    df["RSI"] = compute_rsi(df["close"])

    last = df.iloc[-1]

    if last["close"] > last["MA20"] and last["close"] > last["MA50"] and last["RSI"] < 65:
        return True, last["close"]

    return False, last["close"]

def send_message(text):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

def main():
    last_ping = 0

    while True:
        now = time.time()

        if now - last_ping > 3600:
            send_message("⚡ البوت يعمل بشكل طبيعي")
            last_ping = now

        for coin in COINS:
            try:
                df = get_klines(coin)
                signal, price = analyze(df)

                if signal:
                    entry = price
                    tp1 = round(entry * 1.02, 4)
                    tp2 = round(entry * 1.05, 4)
                    sl = round(entry * 0.97, 4)

                    msg = f"""
🚀 فرصة شراء قوية

العملة: {coin}
السعر الحالي: {entry}

🎯 أهداف:
TP1: {tp1}
TP2: {tp2}

🛑 وقف الخسارة:
SL: {sl}

⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
                    send_message(msg)

            except Exception as e:
                print("Error:", e)

        time.sleep(30)

if __name__ == "__main__":
    main()
