import os
import time
import pandas as pd
from binance.client import Client
import ta
import requests
from datetime import datetime, timedelta

# ====== CONFIG ======
TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
CHAT_ID = os.getenv("7960335113")

INTERVAL = Client.KLINE_INTERVAL_15MINUTE
LIMIT = 120
MIN_SCORE = 6
MIN_VOLUME_24H = 5_000_000
COOLDOWN_MINUTES = 60

client = Client()  # بدون API نهائيًا
sent_coins = {}

# ====== TELEGRAM ======
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# ====== BTC FILTER ======
def btc_trend_ok():
    klines = client.get_klines(symbol="BTCUSDT", interval=INTERVAL, limit=50)
    df = pd.DataFrame(klines, columns=[
        'time','open','high','low','close','volume',
        'close_time','qav','trades','taker_base','taker_quote','ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['ma25'] = ta.trend.sma_indicator(df['close'], window=25)
    last = df.iloc[-1]

    return last['close'] > last['ma25']

# ====== ANALYZE ======
def analyze(symbol):
    try:
        ticker = client.get_ticker(symbol=symbol)

        change_24h = float(ticker['priceChangePercent'])
        volume_24h = float(ticker['quoteVolume'])

        if volume_24h < MIN_VOLUME_24H:
            return

        klines = client.get_klines(symbol=symbol, interval=INTERVAL, limit=LIMIT)

        df = pd.DataFrame(klines, columns=[
            'time','open','high','low','close','volume',
            'close_time','qav','trades','taker_base','taker_quote','ignore'
        ])

        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['volume'] = df['volume'].astype(float)

        df['ma7'] = ta.trend.sma_indicator(df['close'], window=7)
        df['ma25'] = ta.trend.sma_indicator(df['close'], window=25)
        df['ma99'] = ta.trend.sma_indicator(df['close'], window=99)
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)

        last = df.iloc[-1]
        score = 0

        breakout = last['close'] > df['high'][-20:-1].max()
        volume_break = last['volume'] > df['volume'].rolling(20).mean().iloc[-1]
        trend_cross = last['ma7'] > last['ma25']
        above_ma99 = last['close'] > last['ma99']
        rsi_good = 50 < last['rsi'] < 72
        change_ok = 2 < change_24h < 18

        if breakout:
            score += 3
        if volume_break:
            score += 2
        if trend_cross:
            score += 2
        if above_ma99:
            score += 1
        if rsi_good:
            score += 1
        if change_ok:
            score += 1

        if score >= MIN_SCORE:
            now = datetime.now()

            if symbol in sent_coins:
                if now - sent_coins[symbol] < timedelta(minutes=COOLDOWN_MINUTES):
                    return

            entry = last['close']
            target1 = entry * 1.025
            target2 = entry * 1.05
            stop = entry * 0.97
            rr = ((target2 - entry) / entry) * 100

            message = f"""
🔥 <b>{symbol}</b>

السعر الحالي: {round(entry,4)}

📌 دخول: {round(entry,4)}
🎯 هدف 1: {round(target1,4)}
🎯 هدف 2: {round(target2,4)}
🛑 وقف: {round(stop,4)}

📊 نسبة ربح محتملة: {round(rr,2)}%
⭐ تقييم الفرصة: {score}/10
💰 حجم 24h: {round(volume_24h/1_000_000,2)}M
"""

            send_telegram(message)
            sent_coins[symbol] = now

    except:
        pass

# ====== MAIN LOOP ======
def main():
    if not btc_trend_ok():
        print("BTC trend not favorable. Skipping cycle.")
        return

    exchange_info = client.get_exchange_info()
    symbols = [
        s['symbol'] for s in exchange_info['symbols']
        if s['quoteAsset'] == 'USDT'
        and s['status'] == 'TRADING'
        and not s['symbol'].endswith("UPUSDT")
        and not s['symbol'].endswith("DOWNUSDT")
    ]

    for symbol in symbols:
        analyze(symbol)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(900)  # كل 15 دقيقة
