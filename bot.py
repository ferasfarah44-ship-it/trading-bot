import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
import telegram

bot = telegram.Bot(token=TELEGRAM_TOKEN)

COINS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","ADAUSDT","DOTUSDT","ATOMUSDT","AVAXUSDT",
    "NEARUSDT","OPUSDT","ARBUSDT","LINAUSDT","XRPUSDT","XLMUSDT","TRXUSDT",
    "BNBUSDT","LINKUSDT","INJUSDT","FETUSDT","TAOUSDT","GRTUSDT","APTUSDT"
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

def compute_macd(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal

def analyze(df):
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()
    df["MA200"] = df["close"].rolling(200).mean()

    df["RSI"] = compute_rsi(df["close"])
    df["MACD"], df["MACD_signal"] = compute_macd(df["close"])

    df["Stoch_K"] = ((df["close"] - df["low"].rolling(14).min()) /
                     (df["high"].rolling(14).max() - df["low"].rolling(14).min())) * 100

    df["Volume_MA"] = df["volume"].rolling(20).mean()

    last = df.iloc[-1]

    score = 0

    if last["close"] > last["MA50"]: score += 1
    if last["close"] > last["MA20"]: score += 1
    if last["MACD"] > last["MACD_signal"]: score += 1
    if 45 < last["RSI"] < 65: score += 1
    if last["volume"] > last["Volume_MA"] * 1.5: score += 1
    if last["Stoch_K"] < 80: score += 1

    if score >= 5:
        return True, last["close"], score
    return False, last["close"], score

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
                signal, price, strength = analyze(df)

                if signal:
                    entry = price
                    tp1 = round(entry * 1.02, 4)
                    tp2 = round(entry * 1.05, 4)
                    sl = round(entry * 0.97, 4)

                    power = ["ضعيف", "متوسط", "قوي", "قوي جدًا", "انفجار"][strength - 1]

                    msg = f"""
🚀 فرصة شراء (نظام PRO هجومي)

العملة: {coin}
السعر الحالي: {entry}

📊 قوة الإشارة: {power}

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

        time.sleep(20)

if __name__ == "__main__":
    main()
