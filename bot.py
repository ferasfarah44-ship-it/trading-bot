import requests
import time
from datetime import datetime

BOT_TOKEN = "PUT_YOUR_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

symbols = ["SOLUSDT","ETHUSDT","ARBUSDT","OPUSDT","NEARUSDT","LINKUSDT"]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)

def get_klines(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=30"
        response = requests.get(url, timeout=10)
        data = response.json()

        # إذا Binance رجع خطأ
        if not isinstance(data, list):
            print(f"Binance error for {symbol}:", data)
            return None

        if len(data) < 20:
            print(f"Not enough data for {symbol}")
            return None

        return data

    except Exception as e:
        print(f"Fetch error {symbol}:", e)
        return None


print("🚀 BOT STARTED")
send_telegram("🚀 البوت اشتغل بنجاح")

last_heartbeat = 0

while True:
    try:
        now = time.time()

        # رسالة تأكيد كل ساعة
        if now - last_heartbeat > 3600:
            send_telegram("✅ البوت يعمل بشكل طبيعي")
            last_heartbeat = now

        for symbol in symbols:
            data = get_klines(symbol)
            if data is None:
                continue

            closes = [float(x[4]) for x in data]
            highs = [float(x[2]) for x in data]
            lows = [float(x[3]) for x in data]

            current_price = closes[-1]
            highest_20 = max(highs[-21:-1])  # أعلى 20 شمعة سابقة

            # شرط اختراق بسيط (فرص يومية)
            if current_price > highest_20:
                entry = round(current_price, 4)
                target = round(entry * 1.03, 4)
                stop = round(entry * 0.98, 4)

                message = f"""
🔥 فرصة جديدة {symbol}

السعر الحالي: {entry}
الهدف: {target} (+3%)
وقف الخسارة: {stop} (-2%)
"""
                print(f"Signal found {symbol}")
                send_telegram(message)

        time.sleep(300)  # يفحص كل 5 دقائق

    except Exception as e:
        print("Main Loop Error:", e)
        time.sleep(60)
