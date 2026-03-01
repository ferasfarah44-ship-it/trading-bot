import requests
import pandas as pd
import time

TELEGRAM_TOKEN = "PUT_YOUR_BOT_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

symbols = ["SOLUSDT","ETHUSDT","ARBUSDT","OPUSDT","NEARUSDT","LINKUSDT"]
interval = "4h"

sent_signals = set()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=200"
    data = requests.get(url).json()
    df = pd.DataFrame(data)
    df = df.iloc[:,0:6]
    df.columns = ["time","open","high","low","close","volume"]
    df["close"] = df["close"].astype(float)
    df["low"] = df["low"].astype(float)
    df["high"] = df["high"].astype(float)
    return df

def analyze(symbol):
    df = get_klines(symbol)

    df["MA7"] = df["close"].rolling(7).mean()
    df["MA25"] = df["close"].rolling(25).mean()
    df["MA100"] = df["close"].rolling(100).mean()
    df["MA200"] = df["close"].rolling(200).mean()

    last = df.iloc[-1]
    support = df["low"].rolling(10).min().iloc[-1]

    trend = (
        last["close"] > last["MA100"] and
        last["close"] > last["MA200"] and
        last["MA7"] > last["MA25"]
    )

    near_support = abs(last["close"] - support) / support < 0.02

    target = last["close"] * 1.03
    space = (target - last["close"]) / last["close"] >= 0.03

    if trend and near_support and space:
        if symbol not in sent_signals:
            message = f"""
🚀 فرصة 24 ساعة

العملة: {symbol}
السعر الحالي: {last['close']:.2f}
سعر الدخول: {last['close']:.2f}
الهدف: {target:.2f}
الربح المتوقع: 3%
            """
            send_telegram(message)
            sent_signals.add(symbol)

while True:
    for s in symbols:
        try:
            analyze(s)
        except:
            pass
    time.sleep(300)
