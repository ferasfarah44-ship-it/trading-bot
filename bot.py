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

daily_pair_count = {}
last_signal_time = {}
last_reset_day = datetime.now(timezone.utc).day

HALAL = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","AVAXUSDT","DOGEUSDT","MATICUSDT","LINKUSDT"
]

# ---------------- TELEGRAM ----------------
def send(msg, keyboard=False):
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "disable_notification": False
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": [
                ["▶️ تشغيل", "⏸ إيقاف"],
                ["🔍 فحص", "📊 الحالة"]
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
def swing_signal(sym):
    global last_reset_day, daily_pair_count, last_signal_time

    current_day = datetime.now(timezone.utc).day
    if current_day != last_reset_day:
        daily_pair_count.clear()
        last_signal_time.clear()
        last_reset_day = current_day

    if sym not in daily_pair_count:
        daily_pair_count[sym] = 0

    if daily_pair_count[sym] >= 15:
        return None

    if sym in last_signal_time:
        if time.time() - last_signal_time[sym] < 45 * 60:
            return None

    try:
        # ===== فلترة الاتجاه 4H =====
        k4h = klines(sym, "4h", 10)
        if not k4h or len(k4h) < 5:
            return None

        closes_4h = [float(k[4]) for k in k4h[-4:-1]]
        if not (closes_4h[2] > closes_4h[1] > closes_4h[0]):
            return None

        # ===== دخول 1H =====
        k1h = klines(sym, "1h", 20)
        if not k1h or len(k1h) < 12:
            return None

        current_price = price(sym)
        if current_price == 0:
            return None

        resistance = max([float(k[2]) for k in k1h[-7:-1]])
        current_close = float(k1h[-1][4])

        if current_close <= resistance:
            return None

        # ===== حجم تداول =====
        volumes = [float(k[5]) for k in k1h[-11:-1]]
        vol_avg = statistics.mean(volumes)
        vol_current = float(k1h[-1][5])

        if vol_current < vol_avg * 1.25:
            return None

        # ===== إدارة مخاطر =====
        stop_loss = resistance * 0.995
        risk = current_price - stop_loss
        if risk <= 0:
            return None

        target1 = current_price + risk * 2
        target2 = current_price + risk * 4

        reward_pct = ((target1 - current_price) / current_price) * 100
        risk_pct = ((current_price - stop_loss) / current_price) * 100

        last_signal_time[sym] = time.time()
        daily_pair_count[sym] += 1

        saudi_time = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%H:%M')

        message = f"""
🚀 فرصة سوينج {sym}

⏰ الوقت: {saudi_time}
💰 السعر: {current_price:.4f}

🎯 الهدف 1: {target1:.4f} (+{reward_pct:.2f}%)
🎯 الهدف 2: {target2:.4f}

🛑 ستوب: {stop_loss:.4f} (-{risk_pct:.2f}%)

📈 الاتجاه 4H صاعد
💧 حجم: {vol_current/vol_avg:.2f}x

⚡ دخول خلال 30 دقيقة
"""

        return message

    except Exception as e:
        print("Error:", e)
        return None


# ---------------- SCAN ----------------
def scan():
    found = 0

    for s in HALAL:
        sig = swing_signal(s)
        if sig:
            send(sig)
            found += 1
            time.sleep(0.6)
            if found >= 3:
                break

    if found > 0:
        total_now = sum(daily_pair_count.values())
        send(f"✅ اكتُشفت {found} فرص | الإجمالي اليوم: {total_now}")


# ---------------- START ----------------
send("🤖 نظام السوينج جاهز", keyboard=True)

while True:

    for u in get_updates():
        LAST_ID = u["update_id"]
        msg = u.get("message", {}).get("text", "").strip()

        if "تشغيل" in msg:
            AUTO = True
            send("✅ التلقائي مفعل")

        elif "إيقاف" in msg:
            AUTO = False
            send("⏸ التلقائي متوقف")

        elif "فحص" in msg:
            scan()

        elif "الحالة" in msg:
            total = sum(daily_pair_count.values())
            send(f"📊 الفرص اليوم: {total}\nالوضع: {'نشط' if AUTO else 'متوقف'}")

    if AUTO and time.time() - last_run > 180:
        scan()
        last_run = time.time()

    time.sleep(3)
