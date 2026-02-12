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

# العملات عالية السيولة
HALAL = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "MATICUSDT", "LINKUSDT",
    "DOTUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "AAVEUSDT"
]

# ---------------- TELEGRAM ----------------
def send(msg, keyboard=False):
    data = {"chat_id": CHAT_ID, "text": msg}
    if keyboard:
        data["reply_markup"] = {
            "keyboard": [
                ["▶️ تشغيل تلقائي", "⏸ إيقاف"],
                ["🔍 فحص الآن", "📊 الحالة"]
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
    global last_reset_day, daily_pair_count
    
    # إعادة تعيين يومياً
    current_day = datetime.now(timezone.utc).day
    if current_day != last_reset_day:
        daily_pair_count = {}
        last_signal_time = {}
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
        
        if not k1h or not k4h or len(k1h) < 15 or len(k4h) < 10:
            return None
        
        current_price = price(sym)
        if current_price == 0:
            return None
        
        # اتجاه 4 ساعات صاعد
        closes_4h = [float(k[4]) for k in k4h[-9:]]
        if closes_4h[-1] < closes_4h[-3] * 1.003:
            return None
        
        # كسر مقاومة 1 ساعة
        resistance = max([float(k[2]) for k in k1h[-7:-1]])
        current_close = float(k1h[-1][4])
        
        if current_close <= resistance * 1.002:
            return None
        
        # تأكيد حجم
        volumes = [float(k[5]) for k in k1h[-7:-1]]
        vol_avg = statistics.mean(volumes)
        vol_current = float(k1h[-1][5])
        if vol_current < vol_avg * 1.8:
            return None
        
        # تجنب الدخول المتأخر
        range_1h = float(k1h[-2][2]) - float(k1h[-2][3])
        if range_1h > 0:
            breakout_margin = (current_price - resistance) / range_1h
            if breakout_margin > 0.6:
                return None
        
        # تأكيد الزخم (شمعة صاعدة)
        current_open = float(k1h[-1][1])
        if current_close < current_open * 1.001:
            return None
        
        # جميع الشروط محققة
        last_signal_time[sym] = time.time()
        daily_pair_count[sym] += 1
        
        # حساب الأهداف والمخاطر
        risk_distance = current_price - resistance
        stop_loss = resistance * 0.995
        
        risk_pct = ((current_price - stop_loss) / current_price) * 100
        if risk_pct > 2.5:
            return None
        
        target1 = current_price + risk_distance * 2.0
        target2 = current_price + risk_distance * 4.0
        target3 = current_price + risk_distance * 6.0
        
        reward_pct_t1 = ((target1 - current_price) / current_price) * 100
        reward_pct_t2 = ((target2 - current_price) / current_price) * 100
        reward_pct_t3 = ((target3 - current_price) / current_price) * 100
        
        # تقدير زمن الوصول
        avg_move_per_hour = risk_distance * 2  # تقدير حركة السعر
        time_to_t1 = max(1, int((target1 - current_price) / avg_move_per_hour))
        time_to_t2 = max(1, int((target2 - current_price) / avg_move_per_hour))
        
        # تنسيق الوقت
        saudi_time = datetime.now().strftime('%H:%M:%S')
        entry_time = saudi_time
        
        # إنشاء الرسالة المحسّنة
        message = f"""╔════════════════════════════════╗
║  🌊 سوينج فرصة ذهبية 🚀        ║
╠════════════════════════════════╣

📅 العملة: #{sym.replace('USDT','')}
⏰ وقت الدخول: {entry_time}

╔════════════════════════════════╗
║ 💰 السعر الحالي: {current_price:,.4f} ║
╠════════════════════════════════╣

🎯 الأهداف مع النسب:
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   🥅 الهدف 1: {target1:,.4f}
      ↗️ +{reward_pct_t1:.2f}% | ⏱️ {time_to_t1}-{time_to_t1+2} ساعات
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   🥅 الهدف 2: {target2:,.4f}
      ↗️ +{reward_pct_t2:.2f}% | ⏱️ {time_to_t2}-{time_to_t2+4} ساعات
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   🥅 الهدف 3: {target3:,.4f}
      ↗️ +{reward_pct_t3:.2f}% | ⏱️ 12-24 ساعة
   ━━━━━━━━━━━━━━━━━━━━━━━━━━

🛑 ستوب لوس: {stop_loss:,.4f}
   ↘️ -{risk_pct:.2f}% (تحت المقاومة مباشرة)

╔════════════════════════════════╗
║ 📊 نسبة المخاطرة/العائد:      ║
║    1 : {reward_pct_t1/risk_pct:.1f} (ممتازة!) 🎯     ║
╠════════════════════════════════╣

📈 التحليل الفني:
   • ✅ كسر مقاومة 1h: {resistance:,.4f}
   • ✅ حجم التداول: {vol_current/vol_avg:.1f}x المتوسط
   • ✅ اتجاه 4h: صاعد ✓
   • ✅ توقيت الدخول: مبكر (ضمن 60%)

💡 ملاحظات:
   • ادخل فوراً للحصول على أفضل سعر
   • ضع ستوب لوس فور الدخول
   • خذ 50% عند الهدف 1، 30% عند الهدف 2، 20% عند الهدف 3

╔════════════════════════════════╗
║ ⚡ صلاحية الإشارة: 30 دقيقة   ║
╚════════════════════════════════╝
"""
        
        return message

    except:
        return None

# ---------------- SCAN ----------------
def scan():
    global daily_pair_count
    current_day = datetime.now(timezone.utc).day
    total_today = sum(daily_pair_count.values()) if daily_pair_count else 0
    
    send(f"🔍 فحص فرص السوينج... (الإجمالي اليوم: {total_today})")
    found = 0
    
    for s in HALAL:
        sig = swing_signal(s)
        if sig:
            send(sig)
            found += 1
            time.sleep(0.7)
            if found >= 5:  # لا نبحث أكثر من 5 فرص في نفس الجلسة
                break
    
    if found == 0:
        send(f"💤 لا توجد فرص الآن (السوق جانبي أو حجم منخفض)")
    else:
        total_now = sum(daily_pair_count.values())
        send(f"✅ تم اكتشاف {found} فرص | الإجمالي اليوم: {total_now}")

# ---------------- START ----------------
send("🤖 نظام السوينج المربح جاهز | رسائل احترافية مع أوقات وأهداف دقيقة", keyboard=True)

while True:
    for u in get_updates():
        LAST_ID = u["update_id"]
        msg = u.get("message", {}).get("text", "").strip()
        
        if not msg:
            continue
            
        if "تشغيل" in msg:
            AUTO = True
            send("🔁 الفحص التلقائي كل 10 دقائق نشط")
        elif "إيقاف" in msg:
            AUTO = False
            send("⏸ التلقائي متوقف")
        elif "فحص" in msg:
            scan()
        elif "الحالة" in msg:
            total_today = sum(daily_pair_count.values()) if daily_pair_count else 0
            send(f"📊 الحالة:\nالوضع: {'نشط' if AUTO else 'متوقف'}\nالفرص اليوم: {total_today}\nالعملات: {len(HALAL)}")

    if AUTO and time.time() - last_run > 600:
        scan()
        last_run = time.time()
    
    time.sleep(3)
