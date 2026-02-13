import requests
import time
import statistics

# ================= الإعدادات الأساسية =================
# تذكر تغيير التوكن لأنه أصبح مكشوفاً للعامة
BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

SENT_ALERTS = {}

# ================= الوظائف الحسابية =================

def calculate_rsi(prices, period=14):
    """حساب مؤشر RSI البسيط"""
    if len(prices) < period + 1: return 50
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(prices, period=20):
    """حساب المتوسط المتحرك الأسي EMA"""
    if len(prices) < period: return prices[-1]
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period  # البداية بمتوسط بسيط
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_targets(current_price):
    entry = current_price
    tp1 = entry * 1.015
    tp2 = entry * 1.030
    sl = entry * 0.980
    return entry, tp1, tp2, sl

# ================= وظيفة التحليل الذكي =================

def get_signal(sym):
    try:
        # جلب 50 شمعة لضمان دقة المؤشرات
        params = {"symbol": sym, "interval": "5m", "limit": 50}
        r = requests.get(f"{BASE}/klines", params=params, timeout=10)
        if r.status_code != 200: return None
        k5 = r.json()
        
        closes = [float(k[4]) for k in k5]
        vols = [float(k[5]) for k in k5]
        
        current_price = closes[-1]
        open_price = float(k5[-1][1])
        vol_now = vols[-1]
        vol_avg = statistics.mean(vols[-20:-1]) # متوسط آخر 20 شمعة
        
        # --- الحسابات الفنية ---
        rsi_val = calculate_rsi(closes)
        ema_val = calculate_ema(closes)
        
        # --- الشروط (مرنة لاقتناص الفرص) ---
        # 1. انفجار فوليوم ملحوظ
        vol_condition = vol_now > vol_avg * 2.0
        # 2. شمعة خضراء وصعود فوق الـ EMA (تأكيد اتجاه)
        trend_condition = current_price > open_price and current_price > ema_val
        # 3. عدم وجود تضخم شرائي قاتل (RSI تحت 75)
        rsi_condition = rsi_val < 75 

        if vol_condition and trend_condition and rsi_condition:
            entry, tp1, tp2, sl = calculate_targets(current_price)
            
            return f"""🚀 **فرصة انفجار سعري مكتشفة**

🪙 العملة: #{sym}
💰 سعر الدخول: {entry:.6f}
📊 مؤشر RSI: {rsi_val:.2f}
📈 فوق المتوسط (EMA 20): ✅

🎯 **الأهداف:**
1️⃣ الهدف الأول: {tp1:.6f} (+1.5%)
2️⃣ الهدف الثاني: {tp2:.6f} (+3.0%)

🚫 **وقف الخسارة:** {sl:.6f} (-2%)

⚠️ *تأكد من مشروعية العملة.*
"""
        return None
    except:
        return None

# ================= إدارة التشغيل =================

def get_all_usdt_pairs():
    try:
        r = requests.get(f"{BASE}/exchangeInfo", timeout=10).json()
        return [s['symbol'] for s in r['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
    except:
        return []

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def run_scanner():
    print("🔎 الرادار يعمل الآن مع RSI و EMA...")
    send_telegram("🛰️ **تم تشغيل الرادار المطور.**\n(مراقبة الفوليوم + RSI + EMA)")
    
    while True:
        all_symbols = get_all_usdt_pairs()
        for symbol in all_symbols:
            signal = get_signal(symbol)
            if signal:
                now = time.time()
                if symbol not in SENT_ALERTS or (now - SENT_ALERTS[symbol] > 7200):
                    send_telegram(signal)
                    SENT_ALERTS[symbol] = now
            time.sleep(0.1) # حماية من الحظر
        
        time.sleep(60)

if __name__ == "__main__":
    run_scanner()
