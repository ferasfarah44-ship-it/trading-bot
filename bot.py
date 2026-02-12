import requests
import time
import statistics
from datetime import datetime, timezone

BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

AUTO = True
LAST_ID = 0
last_run = 0
COOLDOWN_HOURS = 2.5
MAX_DAILY_PER_PAIR = 4

daily_pair_count = {}
last_signal_time = {}
last_reset_day = datetime.now(timezone.utc).day

HALAL = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","AVAXUSDT","DOGEUSDT","MATICUSDT","LINKUSDT",
    "DOTUSDT","LTCUSDT","UNIUSDT","ATOMUSDT","AAVEUSDT"
]

# ---------------- TELEGRAM ----------------
def send(msg, keyboard=False, alert=False):
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "disable_notification": False  # مهم للصوت
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": [
                ["▶️ تشغيل تلقائي", "⏸ إيقاف"],
                ["🔍 فحص الآن", "📊 الحالة"]
            ],
            "resize_keyboard": True
        }

    if alert:
        data["text"] = "🚨🚨 تنبيه فرصة تداول 🚨🚨\n\n" + msg

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
def klines(sym, interval, limit=50):
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
def swing_signal(sym):
    global last_reset_day, daily_pair_count, last_signal_time

    current_day = datetime.now(timezone.utc).day
    if current_day != last_reset_day:
        daily_pair_count.clear()
        last_signal_time.clear()
        last_reset_day = current_day

    if sym not in daily_pair_count:
        daily_pair_count[sym] = 0

    if daily_pair_count[sym] >= MAX_DAILY_PER_PAIR:
        return None

    if sym in last_signal_time:
        if time.time() - last_signal_time[sym] < COOLDOWN_HOURS * 3600:
            return None

    try:
        k1h = klines(sym, "1h", 25)
        k4h = klines(sym, "4h", 20)

        if not k1h or not k4h:
            return None

        current_price = price(sym)
        if current_price == 0:
            return None

        closes_4h = [float(k[4]) for k in k4h[-9:]]
        if closes_4h[-1] < closes_4h[-3] * 1.003:
            return None

        resistance = max([float(k[2]) for k in k1h[-7:-1]])
        current_close = float(k1h[-1][4])

        if current_close <= resistance * 1.002:
            return None

        volumes = [float(k[5]) for k in k1h[-7:-1]]
        vol_avg = statistics.mean(volumes)
        vol_current = float(k1h[-1][5])

        if vol_current < vol_avg * 1.8:
            return None

        current_open = float(k1h[-1][1])
        if current_close < current_open:
            return None

        last_signal_time[sym] = time.time()
        daily_pair_count[sym] += 1

        stop_loss = resistance * 0.995
        target = current_price + (current_price - resistance) * 2

        message = f"""
🌊 فرصة سوينج قوية

العملة: {sym}
السعر: {current_price:.4f}

🎯 الهدف: {target:.4f}
🛑 الستوب: {stop_loss:.4f}

⚡ صلاحية الإشارة: 30 دقيقة
"""

        return message

    except:
        return None

# ---------------- SCAN ----------------
def scan():
    total_today = sum(daily_pair_count.values()) if daily_pair_count else 0
    send(f"🔍 فحص فرص السوينج... (اليوم: {total_today})")

    found = 0

    for s in HALAL:
        sig = swing_signal(s)
        if sig:
            send(sig, alert=True)  # هنا التنبيه القوي
            found += 1
            time.sleep(0.7)

    if found == 0:
        send("💤 لا توجد فرص حالياً")
    else:
        send(f"✅ تم اكتشاف {found} فرص")

# ---------------- START ----------------
send("🤖 نظام السوينج شغال", keyboard=True)

while True:

    for u in get_updates():
        LAST_ID = u["update_id"]
        msg = u.get("message", {}).get("text", "").strip()

        if not msg:
            continue

        if "تشغيل" in msg:
            AUTO = True
            send("🔁 التلقائي مفعل")

        elif "إيقاف" in msg:
            AUTO = False
            send("⏸ التلقائي متوقف")

        elif "فحص" in msg:
            scan()

        elif "الحالة" in msg:
            total_today = sum(daily_pair_count.values())
            send(f"📊 الحالة:\nالوضع: {'نشط' if AUTO else 'متوقف'}\nالفرص اليوم: {total_today}")

    if AUTO and time.time() - last_run > 600:
        scan()
        last_run = time.time()

    time.sleep(3)
