import requests
import time
from datetime import datetime

BOT_TOKEN = "PUT_YOUR_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

symbols = ["SOLUSDT","ETHUSDT","ARBUSDT","OPUSDT","NEARUSDT","LINKUSDT"]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=30"
    return requests.get(url).json()

print("BOT STARTED")

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

            closes = [float(x[4]) for x in data]
            highs = [float(x[2]) for x in data]
            lows = [float(x[3]) for x in data]

            current_price = closes[-1]
            highest = max(highs[:-1])
            lowest = min(lows[:-1])

            # شرط بسيط: اختراق أعلى 20 شمعة
            if current_price > highest:
                entry = current_price
                target = round(entry * 1.03, 3)
                stop = round(entry * 0.98, 3)

                message = f"""
🔥 فرصة جديدة {symbol}

السعر الحالي: {entry}
الهدف: {target} (+3%)
وقف الخسارة: {stop} (-2%)
"""
                send_telegram(message)

        time.sleep(300)  # كل 5 دقائق

    except Exception as e:
        print("ERROR:", e)
        time.sleep(60)
