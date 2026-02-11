import requests
import time
import statistics

BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

AUTO = True
LAST_ID = 0
last_run = 0

HALAL = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","ADAUSDT",
    "XRPUSDT","AVAXUSDT","DOTUSDT","LINKUSDT","HOTUSDT"
]

# ---------------- TELEGRAM ----------------

def send(msg, keyboard=False):
    data = {"chat_id": CHAT_ID, "text": msg}
    if keyboard:
        data["reply_markup"] = {
            "keyboard": [
                ["▶️ تشغيل تلقائي","⏸ إيقاف"],
                ["🔍 فحص الآن","📊 الحالة"]
            ],
            "resize_keyboard": True
        }
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=data,
            timeout=10
        )
    except:
        pass


def get_updates():
    global LAST_ID
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": LAST_ID + 1, "timeout": 25},
            timeout=30
        ).json()
        return r.get("result", [])
    except:
        return []

# ---------------- BINANCE ----------------

def klines(sym, interval, limit=30):
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

def breakout_signal(sym):
    try:
        k5 = klines(sym,"5m",30)
        k15 = klines(sym,"15m",30)
        k1h = klines(sym,"1h",30)

        if not k5 or not k15 or not k1h:
            return None

        close = float(k5[-1][4])
        high_prev = max(float(k[2]) for k in k5[:-1])

        vols = [float(k[5]) for k in k5[:-1]]
        vol_now = float(k5[-1][5])
        vol_avg = statistics.mean(vols)

        if vol_now < vol_avg * 1.8:
            return None
        if close <= high_prev:
            return None
        if float(k15[-1][4]) <= float(k15[-2][4]):
            return None
        if float(k1h[-1][4]) < float(k1h[-2][4]):
            return None

        p = price(sym)

        return f"""🚀 بداية صعود (حلال)
{sym}

💰 السعر: {p:.6f}
💧 زيادة سيولة قوية
📈 كسر 5M + تأكيد 15M + 1H صاعد
"""

    except:
        return None

# ---------------- SCAN ----------------

def scan():
    send("🤖 بدأ الفحص")
    found = 0
    for s in HALAL:
        sig = breakout_signal(s)
        if sig:
            send(sig)
            found += 1
        if found == 3:
            break

    if found == 0:
        send("🔍 لا توجد فرص حالياً")

    send("✅ انتهى الفحص")

# ---------------- START ----------------

send("🤖 النظام شغال | تلقائي مفعل", keyboard=True)

while True:

    for u in get_updates():
        LAST_ID = u["update_id"]
        msg = u.get("message", {}).get("text","")

        if "تشغيل" in msg:
            AUTO = True
            send("🔁 تم تشغيل التلقائي")

        elif "إيقاف" in msg:
            AUTO = False
            send("⏸ تم إيقاف التلقائي")

        elif "فحص" in msg:
            scan()

        elif "الحالة" in msg:
            send("📊 الحالة: " + ("🔁 تلقائي" if AUTO else "⏸ متوقف"))

    if AUTO and time.time() - last_run > 300:
        scan()
        last_run = time.time()

    time.sleep(3)
