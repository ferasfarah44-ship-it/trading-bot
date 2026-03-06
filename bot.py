import requests
import os
import time

print("ANALYSIS BOT VERSION 3")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = [
"SOLUSDT",
"ETHUSDT",
"ARBUSDT",
"LINKUSDT",
"NEARUSDT",
"OPUSDT"
]

def send(msg):

    if not BOT_TOKEN or not CHAT_ID:
        print("telegram variables missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg
        })

        print("telegram status:", r.status_code)

    except Exception as e:
        print("telegram error:", e)


def get_data(symbol):

    try:

        url = "https://api.bybit.com/v5/market/kline"

        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": "15",
            "limit": 120
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if "result" not in data:
            print("bad response:", data)
            return None, None

        candles = data["result"]["list"]

        closes = []
        volumes = []

        for c in candles:

            closes.append(float(c[4]))
            volumes.append(float(c[5]))

        closes.reverse()
        volumes.reverse()

        return closes, volumes

    except Exception as e:

        print("bybit error:", e)
        return None, None


def ema(data, period):

    k = 2 / (period + 1)
    ema_val = data[0]

    for price in data[1:]:
        ema_val = price * k + ema_val * (1 - k)

    return ema_val


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

    closes, volumes = get_data(symbol)

    if closes is None:
        return None

    price = closes[-1]

    ema9 = ema(closes[-20:], 9)
    ema21 = ema(closes[-40:], 21)

    r = rsi(closes)

    vol_now = volumes[-1]
    vol_prev = volumes[-2]

    print(symbol, "RSI:", round(r,2), "EMA9:", round(ema9,2), "EMA21:", round(ema21,2))

    if ema9 > ema21 and 40 < r < 65 and vol_now > vol_prev:

        return f"""
🚀 فرصة سكالبينغ

العملة: {symbol}
السعر: {price}

RSI: {round(r,2)}
EMA9>EMA21
Volume rising
"""

    return None


send("🚀 bot started")


while True:

    try:

        print("starting analysis cycle")

        for symbol in SYMBOLS:

            signal = analyze(symbol)

            if signal:
                send(signal)

            time.sleep(2)

        print("cycle done")

        time.sleep(900)

    except Exception as e:

        print("loop error:", e)
        time.sleep(60)
