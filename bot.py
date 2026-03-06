import requests
import os
import time

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "NEARUSDT",
    "LINKUSDT",
    "OPUSDT",
    "ARBUSDT"
]

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

def get_data(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "15m",
        "limit": 100
    }
    r = requests.get(url, params=params)
    data = r.json()
    closes = [float(x[4]) for x in data]
    return closes

def rsi(data, period=14):
    gains = []
    losses = []

    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyze(symbol):

    closes = get_data(symbol)
    price = closes[-1]

    r = rsi(closes)

    if r < 30:
        return f"""
🚀 فرصة شراء

العملة: {symbol}
السعر: {price}
RSI: {round(r,2)}
"""

    if r > 70:
        return f"""
⚠️ احتمال هبوط

العملة: {symbol}
السعر: {price}
RSI: {round(r,2)}
"""

    return None


send("🚀 بوت تحليل العملات بدأ")

while True:

    try:

        for s in SYMBOLS:

            signal = analyze(s)

            if signal:
                send(signal)

            time.sleep(2)

        print("analysis done")

        time.sleep(900)

    except Exception as e:
        print("error:", e)
