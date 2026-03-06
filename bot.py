import requests
import time
import os
import numpy as np

print("ANALYSIS BOT VERSION 6")

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
            "days": "1"
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if "prices" not in data:
            print("coingecko skip:", symbol)
            return None

        prices = data["prices"]

        if len(prices) < 60:
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

    r = rsi(closes)

    e9 = ema(closes, 9)[-1]
    e21 = ema(closes, 21)[-1]

    price = closes[-1]

    print(symbol, "RSI:", round(r,2), "EMA9:", round(e9,2), "EMA21:", round(e21,2))

    signal = None

    if r < 35 and e9 > e21:
        signal = "BUY"

    elif r > 65 and e9 < e21:
        signal = "SELL"

    if signal:

        msg = f"""
🔥 SIGNAL

PAIR: {symbol}
TYPE: {signal}

PRICE: {round(price,4)}
RSI: {round(r,2)}

EMA9: {round(e9,2)}
EMA21: {round(e21,2)}
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
