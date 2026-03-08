import os
import requests
import pandas as pd
import time
import ta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

coins = [
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","AVAXUSDT","DOTUSDT","MATICUSDT","LINKUSDT",
"ATOMUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT","SUIUSDT","SEIUSDT","TIAUSDT","FTMUSDT",
"ALGOUSDT","FILUSDT","ICPUSDT","EGLDUSDT","XTZUSDT","THETAUSDT","AAVEUSDT","SNXUSDT","CRVUSDT","UNIUSDT",
"LDOUSDT","RUNEUSDT","KAVAUSDT","ROSEUSDT","MINAUSDT","IOTAUSDT","ZILUSDT","DYDXUSDT","IMXUSDT","ENSUSDT",
"COMPUSDT","1INCHUSDT","BALUSDT","YFIUSDT","GMXUSDT","STXUSDT","KSMUSDT","OCEANUSDT","SKLUSDT","ANKRUSDT"
]

def send_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload)
    except:
        pass


def get_data(symbol):

    try:

        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=200"

        data = requests.get(url).json()

        df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","num_trades",
        "taker_base_vol","taker_quote_vol","ignore"
        ])

        df = df[["open","high","low","close","volume"]]

        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["open"] = df["open"].astype(float)

        return df

    except:
        return None


def analyze(symbol):

    df = get_data(symbol)

    if df is None:
        return

    try:

        df["ema20"] = ta.trend.ema_indicator(df["close"],20)

        df["rsi"] = ta.momentum.rsi(df["close"],14)

        macd = ta.trend.MACD(df["close"])

        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        price = df["close"].iloc[-1]
        ema20 = df["ema20"].iloc[-1]
        rsi = df["rsi"].iloc[-1]

        macd_val = df["macd"].iloc[-1]
        macd_signal = df["macd_signal"].iloc[-1]

        volume = df["volume"].iloc[-1]

        avg_volume = df["volume"].rolling(20).mean().iloc[-1]

        resistance = df["high"].rolling(20).max().iloc[-2]

        candle_size = abs(df["close"].iloc[-1] - df["open"].iloc[-1])

        avg_candle = abs(df["close"] - df["open"]).rolling(20).mean().iloc[-1]

        # 🔥 STRONG SIGNAL
        if price > ema20 and rsi > 50 and macd_val > macd_signal and (price > resistance or volume > avg_volume * 1.5):

            send_telegram(f"""
🔥 STRONG SIGNAL

Coin: {symbol}
Entry: {price}

TP1: {price*1.03}
TP2: {price*1.06}
TP3: {price*1.10}

SL: {price*0.96}
""")

        # 📈 TREND
        elif price > ema20 and rsi > 50 and macd_val > macd_signal:

            send_telegram(f"""
📈 TREND SIGNAL

Coin: {symbol}
Entry: {price}

TP1: {price*1.02}
TP2: {price*1.04}
TP3: {price*1.06}

SL: {price*0.97}
""")

        # 🚀 BREAKOUT
        elif price > resistance or volume > avg_volume * 1.5:

            send_telegram(f"""
🚀 BREAKOUT SIGNAL

Coin: {symbol}
Entry: {price}

TP1: {price*1.03}
TP2: {price*1.06}
TP3: {price*1.10}

SL: {price*0.96}
""")

        # 🚨 PUMP ALERT
        elif volume > avg_volume * 2 and rsi > 55 and price > ema20:

            send_telegram(f"""
🚨 PUMP ALERT

Coin: {symbol}

Price: {price}

Volume Spike Detected
""")

        # 🐋 WHALE ACTIVITY
        elif volume > avg_volume * 3 and candle_size > avg_candle * 2:

            send_telegram(f"""
🐋 WHALE ACTIVITY DETECTED

Coin: {symbol}

Large Volume + Large Candle

Price: {price}
""")

        # ⚡ EARLY BREAKOUT
        elif price > resistance * 0.98 and volume > avg_volume * 1.3 and price > ema20:

            send_telegram(f"""
⚡ EARLY BREAKOUT

Coin: {symbol}

Price: {price}

Resistance: {resistance}

Possible Breakout Soon
""")

    except:
        pass


def run_bot():

    send_telegram("✅ Crypto Signal Bot Started")

    last_heartbeat = time.time()

    while True:

        for coin in coins:
            analyze(coin)

        if time.time() - last_heartbeat > 3600:

            send_telegram("🤖 Bot Running Normally")

            last_heartbeat = time.time()

        time.sleep(300)


run_bot()
