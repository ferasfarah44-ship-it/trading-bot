import requests
import time

TELEGRAM_TOKEN = "PUT_YOUR_BOT_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

symbols = ["SOLUSDT","ETHUSDT","ARBUSDT","OPUSDT","NEARUSDT","LINKUSDT"]
interval = "4h"

sent = set()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=200"
    data = requests.get(url).json()
    return data

def moving_average(data, period):
    closes = [float(x[4]) for x in data]
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

def analyze(symbol):
    data = get_klines(symbol)
    closes = [float(x[4]) for x in data]
    lows = [float(x[3]) for x in data]

    current_price = closes[-1]

    ma7 = moving_average(data, 7)
    ma25 = moving_average(data, 25)
    ma100 = moving_average(data, 100)
    ma200 = moving_average(data, 200)

    if None in [ma7, ma25, ma100, ma200]:
        return

    support = min(lows[-10:])

    trend = (
        current_price > ma100 and
        current_price > ma200 and
        ma7 > ma25
    )

    near_support = abs(current_price - support) / support < 0.02

    target = current_price * 1.03
    percent = ((target - current_price) / current_price) * 100

    if trend and near_support:
        if symbol not in sent:
            msg = f"""
🚀 فرصة 24 ساعة

العملة: {symbol}
السعر الحالي: {current_price:.2f}
الدخول: {current_price:.2f}
الهدف: {target:.2f}
نسبة الربح: {percent:.2f}%
            """
            send_telegram(msg)
            sent.add(symbol)

while True:
    for s in symbols:
        try:
            analyze(s)
        except:
            pass
    time.sleep(300)
