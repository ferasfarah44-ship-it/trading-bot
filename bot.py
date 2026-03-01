import requests
import time

TELEGRAM_TOKEN = "PUT_YOUR_BOT_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

symbols = ["SOLUSDT","ETHUSDT","ARBUSDT","OPUSDT","NEARUSDT","LINKUSDT"]
interval = "4h"

sent_today = {}
last_heartbeat = 0

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=200"
    return requests.get(url).json()

def moving_average(data, period):
    closes = [float(x[4]) for x in data]
    return sum(closes[-period:]) / period

def analyze(symbol):
    global sent_today

    data = get_klines(symbol)

    closes = [float(x[4]) for x in data]
    highs = [float(x[2]) for x in data]
    volumes = [float(x[5]) for x in data]

    current = closes[-1]

    ma7 = moving_average(data, 7)
    ma25 = moving_average(data, 25)
    ma100 = moving_average(data, 100)

    avg_vol = sum(volumes[-10:]) / 10
    last_vol = volumes[-1]

    recent_high = max(highs[-20:])
    space_up = (recent_high - current) / current

    trend = current > ma100 and ma7 > ma25
    volume_ok = last_vol > avg_vol
    space_ok = space_up > 0.03  # 3% مساحة صعود

    if trend and volume_ok and space_ok:
        today = time.strftime("%Y-%m-%d")
        if sent_today.get(symbol) != today:

            target = current * 1.03
            percent = 3

            msg = f"""
🚀 صفقة 24 ساعة

العملة: {symbol}
السعر الحالي: {current:.2f}
الدخول: {current:.2f}
الهدف: {target:.2f}
نسبة الربح: {percent}%
            """

            send_telegram(msg)
            sent_today[symbol] = today

while True:
    current_time = time.time()

    # تحليل العملات
    for s in symbols:
        try:
            analyze(s)
        except Exception as e:
            print("Error:", e)

    # رسالة تأكيد كل ساعة
    if current_time - last_heartbeat >= 3600:
        send_telegram("✅ البوت يعمل بشكل طبيعي")
        last_heartbeat = current_time

    time.sleep(300)  # فحص كل 5 دقائق
