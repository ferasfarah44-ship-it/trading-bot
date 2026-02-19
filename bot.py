import requests
import pandas as pd
import time
import datetime

BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"

INTERVAL = "15m"
CHECK_INTERVAL = 300
BASE_URL = "https://data-api.binance.vision"

sent_signals = {}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except:
        pass

def get_usdt_pairs():
    try:
        url = f"{BASE_URL}/api/v3/ticker/price"
        data = requests.get(url, timeout=10).json()
        return [x["symbol"] for x in data if x["symbol"].endswith("USDT")]
    except:
        return []

def get_klines(symbol):
    try:
        url = f"{BASE_URL}/api/v3/klines"
        params = {"symbol": symbol, "interval": INTERVAL, "limit": 120}
        data = requests.get(url, params=params, timeout=10).json()

        if not isinstance(data, list):
            return None

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "_","_","_","_","_","_"
        ])

        df["close"] = pd.to_numeric(df["close"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        df["volume"] = pd.to_numeric(df["volume"])

        return df
    except:
        return None

def check_cross(symbol):
    global sent_signals

    df = get_klines(symbol)
    if df is None or len(df) < 50:
        return

    df["MA5"] = df["close"].rolling(5).mean()
    df["MA25"] = df["close"].rolling(25).mean()
    df["VOL_MA20"] = df["volume"].rolling(20).mean()

    df.dropna(inplace=True)

    if len(df) < 2:
        return

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    bullish_cross = (
        prev["MA5"] < prev["MA25"] and
        curr["MA5"] > curr["MA25"] and
        curr["close"] > curr["MA25"] and
        curr["MA5"] > prev["MA5"] and
        curr["MA25"] > prev["MA25"] and
        curr["volume"] > curr["VOL_MA20"]
    )

    if not bullish_cross:
        return

    if symbol in sent_signals and sent_signals[symbol] == curr["time"]:
        return

    entry = curr["close"]
    target = df["high"].tail(20).max()
    stop = df["low"].tail(20).min()

    if entry <= stop:
        return

    rr = round((target - entry) / (entry - stop), 2)

    if rr < 1.5:
        return

    message = f"""
🚀 تقاطع قوي MA5 / MA25

{symbol}

📍 دخول: {entry}
🎯 الهدف: {target}
🛑 الوقف: {stop}
⚖ R/R: {rr}

🔥 فلترة احترافية
⏰ {datetime.datetime.now().strftime("%H:%M")}
"""
    send_telegram(message)
    sent_signals[symbol] = curr["time"]

print("تم تشغيل البوت:", datetime.datetime.now())

while True:

    SYMBOLS = get_usdt_pairs()

    if not SYMBOLS:
        print("فشل تحميل الأزواج")
        time.sleep(10)
        continue

    print("عدد الأزواج:", len(SYMBOLS))

    for symbol in SYMBOLS:
        try:
            check_cross(symbol)
        except:
            pass

    for i in range(CHECK_INTERVAL):
        time.sleep(1)
        if i % 60 == 0:
            print("يعمل...", datetime.datetime.now())
