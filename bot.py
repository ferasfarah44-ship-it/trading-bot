import os
import requests
import pandas as pd
import time
import ta

# ===== TELEGRAM SETTINGS FROM RAILWAY =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# ===== COINS TO ANALYZE =====
coins = [
"BTCUSDT","ETHUSDT","SOLUSDT","NEARUSDT",
"BNBUSDT","AVAXUSDT","MATICUSDT","ATOMUSDT",
"LINKUSDT","ARBUSDT","OPUSDT"
]

# ===== TELEGRAM SEND FUNCTION =====
def send_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": message
    }

    try:
        r = requests.post(url, data=payload)
        print(r.text)
    except Exception as e:
        print("telegram error:", e)


# ===== GET BINANCE DATA =====
def get_data(symbol):

    try:

        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=200"

        data = requests.get(url).json()

        df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","num_trades",
        "taker_base_vol","taker_quote_vol","ignore"
        ])

        df = df[["close","volume"]]

        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        if len(df) < 60:
            return None

        return df

    except:
        return None


# ===== ANALYSIS =====
def analyze(symbol):

    df = get_data(symbol)

    if df is None:
        return

    try:

        df["ema20"] = ta.trend.ema_indicator(df["close"],20)
        df["ema50"] = ta.trend.ema_indicator(df["close"],50)

        df["rsi"] = ta.momentum.rsi(df["close"],14)

        macd = ta.trend.MACD(df["close"])

        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        price = df["close"].iloc[-1]
        ema20 = df["ema20"].iloc[-1]
        ema50 = df["ema50"].iloc[-1]
        rsi = df["rsi"].iloc[-1]

        macd_val = df["macd"].iloc[-1]
        macd_signal = df["macd_signal"].iloc[-1]

        volume = df["volume"].iloc[-1]
        volume_prev = df["volume"].iloc[-2]

        # ===== SIGNAL CONDITIONS =====
        if price > ema20 and ema20 > ema50 and rsi > 50 and macd_val > macd_signal and volume > volume_prev:

            entry = price

            tp1 = price * 1.03
            tp2 = price * 1.06
            tp3 = price * 1.10

            sl = price * 0.97

            message = f"""
🚀 CRYPTO SIGNAL

Coin: {symbol}

Price: {price:.4f}

Entry: {entry:.4f}

🎯 Targets
TP1: {tp1:.4f}
TP2: {tp2:.4f}
TP3: {tp3:.4f}

🛑 StopLoss: {sl:.4f}
"""

            send_telegram(message)

    except:
        pass


# ===== MAIN BOT LOOP =====
def run_bot():

    send_telegram("✅ Crypto Signal Bot Started")

    last_heartbeat = time.time()

    while True:

        for coin in coins:
            analyze(coin)

        # رسالة كل ساعة للتأكد أن البوت يعمل
        if time.time() - last_heartbeat > 3600:

            send_telegram("🤖 Bot Running Normally")

            last_heartbeat = time.time()

        time.sleep(300)


run_bot()
