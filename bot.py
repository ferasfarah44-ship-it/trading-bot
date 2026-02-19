import requests
import pandas as pd
import time
import datetime

# ====== إعداداتك ======
BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"

SYMBOLS = ["ZROUSDT", "C98USDT", "OGUSDT"]
INTERVAL = "15m"
CHECK_INTERVAL = 300  # كل 5 دقائق
SWING_LOOKBACK = 20

# =======================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def get_klines(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": INTERVAL, "limit": 200}
    response = requests.get(url, params=params)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df

def find_swing_high(df):
    recent = df.tail(SWING_LOOKBACK)
    return recent["high"].max()

def find_swing_low(df):
    recent = df.tail(SWING_LOOKBACK)
    return recent["low"].min()

def check_cross(symbol):
    df = get_klines(symbol)

    df["MA5"] = df["close"].rolling(5).mean()
    df["MA25"] = df["close"].rolling(25).mean()

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    if prev["MA5"] < prev["MA25"] and curr["MA5"] > curr["MA25"]:

        entry = curr["close"]
        target = find_swing_high(df)
        stop = find_swing_low(df)

        rr = round((target - entry) / (entry - stop), 2) if entry > stop else 0

        message = f"""
🚀 إشارة تقاطع MA5 مع MA25

العملة: {symbol}
الإطار: {INTERVAL}

📍 دخول: {entry:.5f}
🎯 الهدف (Swing High): {target:.5f}
🛑 وقف الخسارة (Swing Low): {stop:.5f}
⚖ نسبة العائد/المخاطرة: {rr}

⏰ الوقت: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
        send_telegram(message)

print("تم تشغيل البوت:", datetime.datetime.now())

while True:
    for symbol in SYMBOLS:
        try:
            print("فحص:", symbol, datetime.datetime.now())
            check_cross(symbol)
        except Exception as e:
            print(f"خطأ في {symbol}: {e}")

    # بدل sleep طويل نخليه نبضات قصيرة
    for i in range(CHECK_INTERVAL):
        time.sleep(1)
        if i % 60 == 0:
            print("يعمل...", datetime.datetime.now())
