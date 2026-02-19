import requests
import pandas as pd
import time
import datetime

BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"

INTERVAL = "15m"
CHECK_INTERVAL = 300
SWING_LOOKBACK = 20

sent_signals = {}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_all_usdt_pairs():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "symbols" not in data:
            print("رد غير متوقع من Binance:", data)
            return []

        symbols = []
        for s in data["symbols"]:
            if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING":
                symbols.append(s["symbol"])

        return symbols

    except Exception as e:
        print("فشل جلب الأزواج:", e)
        return []

def get_klines(symbol):
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": INTERVAL, "limit": 200}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if not isinstance(data, list):
            return None

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "_","_","_","_","_","_"
        ])

        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
        df["low"] = pd.to_numeric(df["low"], errors="coerce")

        df.dropna(inplace=True)

        return df

    except:
        return None

def find_swing_high(df):
    return df.tail(SWING_LOOKBACK)["high"].max()

def find_swing_low(df):
    return df.tail(SWING_LOOKBACK)["low"].min()

def check_cross(symbol):
    global sent_signals

    df = get_klines(symbol)

    if df is None or len(df) < 30:
        return

    df["MA5"] = df["close"].rolling(5).mean()
    df["MA25"] = df["close"].rolling(25).mean()

    df.dropna(inplace=True)

    if len(df) < 2:
        return

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    if prev["MA5"] < prev["MA25"] and curr["MA5"] > curr["MA25"]:

        last_time = curr["time"]

        if symbol in sent_signals and sent_signals[symbol] == last_time:
            return

        entry = curr["close"]
        target = find_swing_high(df)
        stop = find_swing_low(df)

        if entry <= stop:
            return

        rr = round((target - entry) / (entry - stop), 2)

        message = f"""
🚀 تقاطع MA5 مع MA25

العملة: {symbol}
الإطار: {INTERVAL}

📍 دخول: {entry}
🎯 الهدف: {target}
🛑 الوقف: {stop}
⚖ R/R: {rr}

⏰ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
        send_telegram(message)
        sent_signals[symbol] = last_time


print("تم تشغيل البوت:", datetime.datetime.now())

# تحميل الأزواج مع إعادة المحاولة
while True:
    SYMBOLS = get_all_usdt_pairs()

    if SYMBOLS:
        print("عدد الأزواج:", len(SYMBOLS))
        break
    else:
        print("فشل تحميل الأزواج - إعادة المحاولة بعد 10 ثواني")
        time.sleep(10)

while True:

    for symbol in SYMBOLS:
        try:
            check_cross(symbol)
        except Exception as e:
            print("خطأ في", symbol)

    # نبضات منع النوم
    for i in range(CHECK_INTERVAL):
        time.sleep(1)
        if i % 60 == 0:
            print("يعمل...", datetime.datetime.now())
