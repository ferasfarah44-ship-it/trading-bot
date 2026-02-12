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
COOLDOWN_HOURS = 1.5  # تبريد 1.5 ساعة (يسمح بفرص أكثر لنفس العملة)
MAX_DAILY_PER_PAIR = 6  # 6 فرص يومياً كحد أقصى للعملة الواحدة
daily_pair_count = {}
last_signal_time = {}
last_reset_day = datetime.now(timezone.utc).day

# العملات عالية السيولة (نركز على 10 عملات رئيسية فقط لزيادة الفرص)
HALAL = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "MATICUSDT", "LINKUSDT"
]

# ---------------- TELEGRAM ----------------
def send(msg, keyboard=False):
    data = {"chat_id": CHAT_ID, "text": msg}
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
    
    # إعادة تعيين يومياً عند منتصف الليل بتوقيت السعودية
    current_day = datetime.now(timezone.utc).day
    if current_day != last_reset_day:
        daily_pair_count = {}
        last_signal_time = {}
        last_reset_day = current_day
    
    # تحديث عداد العملة
    if sym not in daily_pair_count:
        daily_pair_count[sym] = 0
    
    # تجنب تجاوز الحد اليومي
    if daily_pair_count[sym] >= MAX_DAILY_PER_PAIR:
        return None
    
    # تجنب التكرار خلال فترة التبريد
    if sym in last_signal_time:
        if time.time() - last_signal_time[sym] < COOLDOWN_HOURS * 3600:
            return None
    
    try:
        # جلب البيانات (نركز على 1 ساعة فقط - أسرع وأكثر حساسية)
        k1h = klines(sym, "1h", 20)
        if not k1h or len(k1h) < 15:
            return None
        
        current_price = price(sym)
        if current_price == 0:
            return None
        
        # ===== الشرط 1: كسر مقاومة 1 ساعة (الأساسي) =====
        # المقاومة = أعلى 5 فترات ساعة سابقة (أكثر حساسية من 7)
        resistance = max([float(k[2]) for k in k1h[-6:-1]])
        current_high = float(k1h[-1][2])
        current_close = float(k1h[-1][4])
        
        # كسر حقيقي (السعر الحالي فوق المقاومة)
        if current_price <= resistance * 1.001:  # 0.1% فقط فوق المقاومة (أكثر حساسية)
            return None
        
        # ===== الشرط 2: تأكيد حجم (مخفف) =====
        volumes = [float(k[5]) for k in k1h[-6:-1]]
        vol_avg = statistics.mean(volumes)
        vol_current = float(k1h[-1][5])
        if vol_current < vol_avg * 1.5:  # 1.5x بدل 1.8x (أكثر حساسية)
            return None
        
        # ===== الشرط 3: زخم إيجابي بسيط =====
        # آخر شمعتين ساعتين صاعدتين (بدون شروط معقدة)
        close_prev = float(k1h[-2][4])
        close_prev2 = float(k1h[-3][4])
        if current_close < close_prev or close_prev < close_prev2:
            return None
        
        # ===== الشرط 4: تجنب الدخول المتأخر (مرن) =====
        range_1h = float(k1h[-2][2]) - float(k1h[-2][3])
        if range_1h > 0:
            breakout_margin = (current_price - resistance) / range_1h
            if breakout_margin > 0.7:  # 70% بدل 60% (يسمح بدخول أسرع)
                return None
        
        # ===== الشرط 5: إدارة مخاطر إلزامية =====
        stop_loss = resistance * 0.993  # 0.7% تحت المقاومة
        risk_pct = ((current_price - stop_loss) / current_price) * 100
        if risk_pct > 2.0:  # لا ندخل إذا المخاطرة > 2%
            return None
        
        # جميع الشروط محققة - إعداد الإشارة
        last_signal_time[sym] = time.time()
        daily_pair_count[sym] += 1
        
        # حساب أهداف ذكية
        risk_distance = current_price - stop_loss
        target1 = current_price + risk_distance * 2.0
        target2 = current_price + risk_distance * 4.0
        target3 = current_price + risk_distance * 6.0
        
        reward_pct_t1 = ((target1 - current_price) / current_price) * 100
        reward_pct_t2 = ((target2 - current_price) / current_price) * 100
        reward_pct_t3 = ((target3 - current_price) / current_price) * 100
        
        # تنسيق الوقت بتوقيت السعودية
        saudi_time = (datetime.now(timezone.utc) + timezone(offset=timezone(timedelta(hours=3)).utcoffset(None))).strftime('%H:%M:%S')
        
        # رسالة احترافية مع كل التفاصيل
        message = f"""╔════════════════════════════════╗
║   🌊 فرصة سوينج #{sym.replace('USDT','')}  🚀  ║
╠════════════════════════════════╣

⏰ وقت الدخول: {saudi_time}
💰 السعر: {current_price:,.4f}

╔════════════════════════════════╗
║  🎯 الأهداف مع النسب:         ║
╠════════════════════════════════╣
║  T1: {target1:,.4f} ↗️ +{reward_pct_t1:.2f}% ║
║  T2: {target2:,.4f} ↗️ +{reward_pct_t2:.2f}% ║
║  T3: {target3:,.4f} ↗️ +{reward_pct_t3:.2f}% ║
╠════════════════════════════════╣
║  🛑 ستوب لوس: {stop_loss:,.4f} ↘️ -{risk_pct:.2f}% ║
╚════════════════════════════════╝

📊 نسبة المخاطرة/العائد: 1:{reward_pct_t1/risk_pct:.1f}
📈 السبب: كسر مقاومة {resistance:,.4f} بحجم {vol_current/vol_avg:.1f}x
⚡ صالح للدخول خلال 20 دقيقة
"""
        
        return message

    except Exception as e:
        # لإزالة التعليق عند الحاجة للتصحيح: print(f"خطأ {sym}: {e}")
        return None

# ---------------- SCAN ----------------
def scan():
    global daily_pair_count
    total_today = sum(daily_pair_count.values()) if daily_pair_count else 0
    
    found = 0
    for s in HALAL:
        sig = swing_signal(s)
        if sig:
            send(sig)
            found += 1
            time.sleep(0.6)
            if found >= 3:  # نكتفي بـ 3 فرص في الجلسة الواحدة
                break
    
    # إرسال ملخص فقط إذا وجدت فرص
    if found > 0:
        total_now = sum(daily_pair_count.values())
        send(f"✅ اكتُشفت {found} فرص | الإجمالي اليوم: {total_now}")

# ---------------- START ----------------
send("🤖 نظام السوينج المحسّن جاهز | شروط واقعية ترصد 3-5 فرص يومياً عالية الجودة", keyboard=True)

while True:
    # معالجة الأوامر
    for u in get_updates():
        LAST_ID = u["update_id"]
        msg = u.get("message", {}).get("text", "").strip()
        
        if "تشغيل" in msg:
            AUTO = True
            send("✅ الفحص التلقائي كل 3 دقائق نشط")
        elif "إيقاف" in msg:
            AUTO = False
            send("⏸ التلقائي متوقف")
        elif "فحص" in msg:
            scan()
        elif "الحالة" in msg:
            total = sum(daily_pair_count.values()) if daily_pair_count else 0
            send(f"📊 الفرص اليوم: {total}\nالوضع: {'نشط' if AUTO else 'متوقف'}")

    # الفحص كل 3 دقائق (التوازن المثالي)
    if AUTO and time.time() - last_run > 180:
        scan()
        last_run = time.time()
    
    time.sleep(3)
