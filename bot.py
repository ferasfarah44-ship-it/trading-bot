import requests
import time
import os
import numpy as np

print("ANALYSIS BOT VERSION 8")

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

COINS = {
    "SOLUSDT": "solana",
    "ETHUSDT": "ethereum",
    "ARBUSDT": "arbitrum",
    "LINKUSDT": "chainlink",
    "NEARUSDT": "near",
    "OPUSDT": "optimism"
}

def send(msg):

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })

    except Exception as e:
        print("telegram error:", e)


def ema(data, period):

    data = np.array(data)
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()

    a = np.convolve(data, weights, mode='full')[:len(data)]
    a[:period] = a[period]

    return a


def rsi(data, period=14):

    data = np.array(data)
    delta = np.diff(data)

    up = delta.clip(min=0)
    down = -1 * delta.clip(max=0)

    ma_up = np.mean(up[-period:])
    ma_down = np.mean(down[-period:])

    if ma_down == 0:
        return 100

    rs = ma_up / ma_down

    return 100 - (100 / (1 + rs))


def get_data(symbol):

    try:

        coin = COINS[symbol]

        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"

        params = {
            "vs_currency": "usd",
            "days": "1",
            "interval": "minutely"
        }

        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        if "prices" not in data:
            return None

        prices = data["prices"]

        if len(prices) < 50:
            return None

        closes = [p[1] for p in prices[-120:]]

        return closes

    except Exception as e:

        print("coingecko error:", e)
        return None


def analyze(symbol):

    closes = get_data(symbol)

    if closes is None:
        return

    price = closes[-1]

    ema9 = ema(closes, 9)[-1]
    ema21 = ema(closes, 21)[-1]
    ema100 = ema(closes, 100)[-1]

    r = rsi(closes)

    score = 0
    reasons = []

    if ema9 > ema21:
        score += 25
        reasons.append("EMA9>EMA21")

    if 40 < r < 65:
        score += 20
        reasons.append("RSI healthy")

    if price > ema100:
        score += 20
        reasons.append("Price above EMA100")

    if closes[-1] > closes[-2]:
        score += 15
        reasons.append("Momentum up")

    # Whale activity
    avg_move = np.mean(np.abs(np.diff(closes[-20:])))
    last_move = abs(closes[-1] - closes[-2])

    whale = False

    if last_move > avg_move * 2:
        whale = True
        score += 30
        reasons.append("Whale activity")

    confidence = score

    print(symbol, "confidence:", confidence)

    if confidence >= 40:

        entry = price
        target1 = price * 1.01
        target2 = price * 1.02
        stop = price * 0.99

        whale_text = ""

        if whale:
            whale_text = "\n🐋 Whale activity detected"

        msg = f"""
🚀 فرصة سكالبينغ

العملة: {symbol}

💰 السعر الحالي: {round(price,4)}
📍 الدخول: {round(entry,4)}

🎯 الهدف 1: {round(target1,4)}
🎯 الهدف 2: {round(target2,4)}

🛑 وقف الخسارة: {round(stop,4)}

📊 RSI: {round(r,2)}
📈 الثقة: {confidence}%

{whale_text}

الأسباب:
{" , ".join(reasons)}
"""

        send(msg)


def cycle():

    print("starting analysis cycle")

    for symbol in COINS:

        analyze(symbol)
        time.sleep(3)

    print("cycle done")


send("bot running...")

while True:

    cycle()

    time.sleep(900)
