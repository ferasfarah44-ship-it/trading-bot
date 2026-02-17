import os
import time
import requests
import pandas as pd
import ta
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
CHAT_ID = os.getenv("7960335113")

MIN_SCORE = 6
MIN_VOLUME_24H = 5_000_000
COOLDOWN_MINUTES = 60

sent_coins = {}

# ===== TELEGRAM =====
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=data)

# ===== GET KLINES =====
def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=120"
    r = requests.get(url)
    return r.json()

# ===== GET 24H TICKER =====
def get_ticker(symbol):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    r = requests.get(url)
    return r.json()

# ===== BTC FILTER =====
def btc_trend_ok():
    data = get_klines("BTCUSDT")
    df = pd.DataFrame(data)
    df[4] = df[4].astype(float)
    df["ma25"] = df[4].rolling(25).mean()
    return df.iloc[-1][4] > df.iloc[-1]["ma25"]

# ===== ANALYZE =====
def analyze(symbol):
    try:
        ticker = get_ticker(symbol)
        volume_24h = float(ticker["quoteVolume"])
        change_24h = float(ticker["priceChangePercent"])

        if volume_24h < MIN_VOLUME_24H:
            return

        klines = get_klines(symbol)
        df = pd.DataFrame(klines)

        df["close"] = df[4].astype(float)
        df["high"] = df[2].astype(float)
        df["volume"] = df[5].astype(float)

        df["ma7"] = df["close"].rolling(7).mean()
        df["ma25"] = df["close"].rolling(25).mean()
        df["ma99"] = df["close"].rolling(99).mean()
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)

        last = df.iloc[-1]
        score = 0

        breakout = last["close"] > df["high"][-20:-1].max()
        volume_break = last["volume"] > df["volume"].rolling(20).mean().iloc[-1]
        trend_cross = last["ma7"] > last["ma25"]
        above_ma99 = last["close"] > last["ma99"]
        rsi_good = 50 < last["rsi"] < 72
        change_ok = 2 < change_24h < 18

        if breakout: score += 3
        if volume_break: score += 2
        if trend_cross: score += 2
        if above_ma99: score += 1
        if rsi_good: score += 1
        if change_ok: score += 1

        if score >= MIN_SCORE:
            now = datetime.now()

            if symbol in sent_coins:
                if now - sent_coins[symbol] < timedelta(minutes=COOLDOWN_MINUTES):
                    return

            entry = last["close"]
            target1 = entry * 1.025
            target2 = entry * 1.05
            stop = entry * 0.97
            rr = ((target2 - entry) / entry) * 100

            message = f"""
🔥 <b>{symbol}</b>

السعر الحالي: {round(entry,4)}
📌 دخول: {round(entry,4)}
🎯 هدف1: {round(target1,4)}
🎯 هدف2: {round(target2,4)}
🛑 وقف: {round(stop,4)}

📊 ربح محتمل: {round(rr,2)}%
⭐ تقييم: {score}/10
💰 حجم 24h: {round(volume_24h/1_000_000,2)}M
"""
            send_telegram(message)
            sent_coins[symbol] = now

    except:
        pass

# ===== MAIN LOOP =====
def main():
    if not btc_trend_ok():
        print("BTC negative, skipping.")
        return

    exchange = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
    symbols = [
        s["symbol"] for s in exchange["symbols"]
        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
        and not s["symbol"].endswith("UPUSDT")
        and not s["symbol"].endswith("DOWNUSDT")
    ]

    for symbol in symbols:
        analyze(symbol)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(900)
