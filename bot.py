import time
import datetime
import os
import pandas as pd
import ccxt
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from telegram import Bot

# Telegram
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TOKEN)

# العملات
cryptocurrencies = [
"BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT",
"ADA/USDT","AVAX/USDT","DOT/USDT","MATIC/USDT","LINK/USDT",
"ATOM/USDT","NEAR/USDT","APT/USDT","ARB/USDT","OP/USDT",
"INJ/USDT","SUI/USDT","SEI/USDT","FTM/USDT","FIL/USDT"
]

# استخدام Kucoin بدل Binance
exchange = ccxt.kucoin({
    "enableRateLimit": True
})

def get_ohlcv(symbol, timeframe="1h", limit=100):

    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

        df = pd.DataFrame(
            bars,
            columns=["timestamp","open","high","low","close","volume"]
        )

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        return df

    except Exception as e:
        print("خطأ", symbol, e)
        return None


def analyze_market(symbol):

    df = get_ohlcv(symbol)

    if df is None or df.empty:
        return None

    close = df["close"]
    high = df["high"]
    volume = df["volume"]

    ema20 = EMAIndicator(close=close, window=20).ema_indicator()
    rsi = RSIIndicator(close=close, window=14).rsi()

    macd = MACD(close=close)

    macd_line = macd.macd()
    signal_line = macd.macd_signal()

    resistance = high.rolling(20).max().iloc[-2]

    return {
        "close": close.iloc[-1],
        "ema20": ema20.iloc[-1],
        "rsi": rsi.iloc[-1],
        "macd": macd_line.iloc[-1],
        "signal": signal_line.iloc[-1],
        "resistance": resistance,
        "volume": volume.iloc[-1],
        "avg_volume": volume.rolling(20).mean().iloc[-1]
    }


def check_conditions(data):

    score = 0

    if data["close"] > data["ema20"]:
        score += 1

    if data["rsi"] > 55:
        score += 1

    if data["macd"] > data["signal"]:
        score += 1

    if data["close"] > data["resistance"]:
        score += 1

    if data["volume"] > data["avg_volume"] * 1.5:
        score += 1

    return score


def create_signal(symbol, price):

    tp1 = price * 1.02
    tp2 = price * 1.04
    tp3 = price * 1.06
    sl = price * 0.97

    return f"""
🚀 Crypto Signal

Coin: {symbol}

Entry: {price}

🎯 TP1: {tp1:.4f}
🎯 TP2: {tp2:.4f}
🎯 TP3: {tp3:.4f}

🛑 StopLoss: {sl:.4f}
"""


def send_message(text):

    try:
        bot.send_message(chat_id=CHAT_ID, text=text)

    except Exception as e:
        print("Telegram error:", e)


send_message("✅ Signal bot started")

last_hour = None

while True:

    now = datetime.datetime.now()

    for symbol in cryptocurrencies:

        data = analyze_market(symbol)

        if data:

            score = check_conditions(data)

            if score >= 3:

                msg = create_signal(symbol, data["close"])

                send_message(msg)

        time.sleep(2)

    if now.hour != last_hour:

        last_hour = now.hour

        send_message("🤖 Bot running normally")

    time.sleep(300)
