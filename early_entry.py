import requests
import time
import statistics
from datetime import datetime, timezone, timedelta

BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

AUTO = True
LAST_ID = 0
last_run = 0

# عملات عالية سيولة
PAIRS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT",
    "XRPUSDT","ADAUSDT","AVAXUSDT","DOGEUSDT",
    "MATICUSDT","LINKUSDT"
]

# ---------------- TELEGRAM ----------------
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

def get_updates():
    global LAST_ID
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": LAST_ID + 1, "timeout": 20},
            timeout=25
        ).json()
        return r.get("result", [])
    except:
        return []

# ---------------- BINANCE ----------------
def klines(sym, interval, limit=100):
    try:
        return requests.get(
            f"{BASE}/klines",
            params={"symbol": sym, "interval": interval, "limit": limit},
            timeout=10
        ).json()
    except:
        return []

def price(sym):
    try:
        return float(requests.get(
            f"{BASE}/ticker/price",
            params={"symbol": sym},
            timeout=10
        ).json()["price"])
    except:
        return 0

# ---------------- STRATEGY ----------------
def early_breakout(sym):

    # اتجاه 4 ساعات
    k4h = klines(sym, "4h", 50)
    if not k4h or len(k4h) < 30:
        return None

    closes_4h = [float(k[4]) for k in k4h]
    ma50_4h = statistics.mean(closes_4h[-50:])
    current_4h = closes_4h[-1]

    if current_4h < ma50_4h:
        return None  # ما في اتجاه صاعد

    # فريم ساعة للدخول
    k1h = klines(sym, "1h", 30)
    if not k1h or len(k1h) < 20:
        return None

    current_price = price(sym)
    if current_price == 0:
        return None

    highs = [float(k[2]) for k in k1h[-6:-1]]
    resistance = max(highs)

    volumes = [float(k[5]) for k in k1h[-6:-1]]
    avg_vol = statistics.mean(volumes)
    current_vol = float(k1h[-1][5])

    # كسر مبكر بحجم جيد
    if current_price > resistance * 1.001 and current_vol > avg_vol * 1.4:

        stop = resistance * 0.992
        risk = current_price - stop

        target1 = current_price + risk * 2
        target2 = current_price + risk * 4

        risk_pct = ((current_price - stop) / current_price) * 100
        t1_pct = ((target1 - current_price) / current_price) * 100
        t2_pct = ((target2 - current_price) / current_price) * 100

        saudi_time = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%H:%M")

        message = f"""
🚀 دخول مبكر {sym.replace('USDT','')}

⏰ {saudi_time}
💰 دخول: {current_price:.4f}

🎯 هدف1: {target1:.4f} (+{t1_pct:.2f}%)
🎯 هدف2: {target2:.4f} (+{t2_pct:.2f}%)

🛑 ستوب: {stop:.4f} (-{risk_pct:.2f}%)

📊 الاتجاه 4H صاعد
⚡ كسر مقاومة بحجم قوي
"""

        return message

    return None

# ---------------- SCAN ----------------
def scan():
    for pair in PAIRS:
        signal = early_breakout(pair)
        if signal:
            send(signal)
            time.sleep(1)

# ---------------- START ----------------
send("⚡ نظام الدخول المبكر جاهز")

while True:

    for u in get_updates():
        LAST_ID = u["update_id"]
        msg = u.get("message", {}).get("text", "")

        if "تشغيل" in msg:
            AUTO = True
            send("✅ مفعل")
        elif "إيقاف" in msg:
            AUTO = False
            send("⏸ متوقف")
        elif "فحص" in msg:
            scan()

    if AUTO and time.time() - last_run > 300:
        scan()
        last_run = time.time()

    time.sleep(5)
