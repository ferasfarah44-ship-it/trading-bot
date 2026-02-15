import requests
import time
import statistics
import threading
import math
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ================== الإعدادات الآمنة ==================
# ⚠️ غيّر هذه القيم فوراً بعد تنزيل الكود:
BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"  # ← استخدم توكن جديد (لا تستخدم هذا)
CHAT_ID = "7960335113"      # ← مثال: "7960335113"
BASE = "https://api.binance.com/api/v3"  # ← بدون مسافات زائدة!

SENT_ALERTS = {}
MIN_ALERT_INTERVAL = 1800  # 30 دقيقة بين إشارات نفس العملة

# ================== خادم الويب (لمنع السبات) ==================
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("✅ الصياد نشط | Hunting Early Moves".encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # إخفاء سجلات الطلبات

def run_web_server():
    try:
        server = HTTPServer(("", 8080), KeepAliveHandler)
        server.serve_forever()
    except:
        pass

threading.Thread(target=run_web_server, daemon=True, name="WebServer").start()

# ================== إرسال تنبيه تلغرام (مُصلح) ==================
def send_telegram(msg, symbol=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        # بناء الأزرار فقط إذا وُجد الرمز
        reply_markup = None
        if symbol:
            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📊 افتح على بايننس",
                            "url": f"https://www.binance.com/en/trade/{symbol}"
                        }
                    ],
                    [
                        {
                            "text": "📈 شارت مباشر",
                            "url": f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol.replace('USDT', 'USDT.P')}"
                        }
                    ]
                ]
            }
        
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }
        
        # إضافة الأزرار فقط إذا موجودة
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        # إرسال الطلب مع معالجة الأخطاء
        r = requests.post(url, json=payload, timeout=10)
        
        # تسجيل النتيجة للتصحيح
        if r.status_code == 200:
            print(f"✅ تلغرام: أُرسلت إشارة {symbol if symbol else 'عامة'}")
            return True
        else:
            print(f"❌ تلغرام فشل (كود {r.status_code}): {r.text[:200]}")
            # محاولة إرسال بدون أزرار
            if "BUTTON_TYPE_INVALID" in r.text or "BUTTONS_INVALID" in r.text:
                print("⚠️ محاولة إرسال بدون أزرار...")
                payload.pop("reply_markup", None)
                r2 = requests.post(url, json=payload, timeout=10)
                if r2.status_code == 200:
                    print("✅ نجاح بعد إزالة الأزرار")
                    return True
                else:
                    print(f"❌ فشل نهائي: {r2.text[:150]}")
            return False
    
    except requests.exceptions.Timeout:
        print("❌ تلغرام: انتهى الوقت المسموح (10 ثوانٍ)")
    except requests.exceptions.ConnectionError:
        print("❌ تلغرام: خطأ في الاتصال بالشبكة")
    except Exception as e:
        print(f"❌ تلغرام استثناء: {type(e).__name__} - {str(e)[:150]}")
    return False

# ================== مؤشرات متقدمة ==================
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0.001 * closes[-1]
    
    tr_values = []
    for i in range(1, len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i-1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)
    
    return sum(tr_values[-period:]) / period

# ================== تحليل الأهداف الديناميكية ==================
def calculate_dynamic_targets(price, highs, lows, closes, rsi, volume_ratio):
    atr = calculate_atr(highs, lows, closes, 14)
    recent_highs = highs[-10:]
    
    # تحديد المقاومة الأقرب
    resistance = min([h for h in recent_highs if h > price * 1.005], default=price * 1.03)
    resistance_dist = (resistance - price) / price
    
    # عوامل تعديل
    rsi_factor = min(1.5, (rsi - 50) / 25) if rsi > 50 else 0.8
    vol_factor = min(1.8, 1 + (volume_ratio - 1) * 0.4)
    
    # هدف أول
    tp1 = price * (1 + resistance_dist * 0.5 * rsi_factor * vol_factor)
    tp1_pct = ((tp1 - price) / price) * 100
    
    # هدف ثاني
    tp2 = resistance * (1 + atr * 0.5 / price)
    tp2_pct = ((tp2 - price) / price) * 100
    
    # هدف ثالث (إذا كان الزخم قوياً)
    tp3 = None
    tp3_pct = None
    if rsi > 65 and volume_ratio > 2.0 and resistance_dist > 0.02:
        tp3 = price * (1 + resistance_dist * 2.5 * rsi_factor * vol_factor)
        tp3_pct = ((tp3 - price) / price) * 100
    
    # وقف الخسارة
    support = min(lows[-5:])
    sl = support * 0.995
    sl_pct = ((price - sl) / price) * 100
    
    # تقييد النسب
    tp1_pct = max(0.7, min(2.5, tp1_pct))
    tp2_pct = max(1.5, min(5.0, tp2_pct))
    if tp3_pct:
        tp3_pct = max(3.0, min(8.0, tp3_pct))
    sl_pct = max(0.8, min(2.0, sl_pct))
    
    return {
        "tp1": price * (1 + tp1_pct/100),
        "tp1_pct": round(tp1_pct, 1),
        "tp2": price * (1 + tp2_pct/100),
        "tp2_pct": round(tp2_pct, 1),
        "tp3": price * (1 + tp3_pct/100) if tp3_pct else None,
        "tp3_pct": round(tp3_pct, 1) if tp3_pct else None,
        "sl": price * (1 - sl_pct/100),
        "sl_pct": round(sl_pct, 1),
        "resistance": resistance,
        "atr_pct": (atr / price) * 100
    }

# ================== كشف الحركة المبكرة ==================
def is_early_move(closes, rsi_values, volumes, current_rsi):
    if len(closes) < 8:
        return False
    
    # الشرط 1: السعر فوق EMA20 بقليل
    price = closes[-1]
    ema20 = calculate_ema(closes, 20)
    if price < ema20 * 1.002:
        return False
    
    # الشرط 2: كسر حديث لـ EMA20
    crosses = 0
    for i in range(-3, 0):
        if closes[i] > calculate_ema(closes[:i], 20):
            crosses += 1
    if crosses < 1:
        return False
    
    # الشرط 3: RSI صاعد ومتوازن
    if current_rsi < 52 or current_rsi > 78:
        return False
    
    rsi_rising = sum(1 for i in range(-4, -1) if rsi_values[i+1] > rsi_values[i]) >= 2
    if not rsi_rising:
        return False
    
    # الشرط 4: الحجم بدأ يرتفع
    vol_now = volumes[-1]
    vol_prev = statistics.mean(volumes[-4:-1])
    if vol_now < vol_prev * 1.3 or vol_now > vol_prev * 3.5:
        return False
    
    # الشرط 5: الحركة لم تكن كبيرة
    recent_move = (closes[-1] - closes[-4]) / closes[-4]
    if recent_move > 0.035:
        return False
    
    return True

def calculate_ema(prices, period):
    if len(prices) < period:
        return prices[-1]
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

# ================== تحليل الإشارة (3 استراتيجيات) ==================
def analyze_symbol(symbol, klines):
    try:
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        opens = [float(k[1]) for k in klines]
        
        price = closes[-1]
        open_price = opens[-1]
        move_pct = (price - open_price) / open_price * 100
        
        # حساب المؤشرات
        rsi = calculate_rsi(closes)
        if not rsi or rsi < 45:
            return None
        
        rsi_values = [calculate_rsi(closes[:i]) for i in range(14, len(closes)+1)]
        rsi_values = [v for v in rsi_values if v is not None]
        
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50)
        volume_ratio = volumes[-1] / (statistics.mean(volumes[-25:]) or 1)
        
        # كشف الحركة المبكرة
        if not is_early_move(closes, rsi_values, volumes, rsi):
            return None
        
        # ===== الاستراتيجية 1: سكالبينج (⚡) =====
        if (price > max(highs[-6:-1]) and
            volume_ratio > 1.6 and
            52 < rsi < 72 and
            move_pct > 0.4):
            strategy = "⚡ سكالبينج مبكر"
            risk_level = "منخفض"
        
        # ===== الاستراتيجية 2: بناء ترند (📈) =====
        elif (ema20 > ema50 * 0.998 and
              price > ema20 * 1.003 and
              volume_ratio > 1.4 and
              55 < rsi < 75 and
              closes[-1] > closes[-3]):
            strategy = "📈 بناء ترند"
            risk_level = "متوسط"
        
        # ===== الاستراتيجية 3: تدفق سيولة (🚀) =====
        elif (volume_ratio > 2.0 and
              move_pct > 0.8 and
              rsi > 58 and
              rsi_values[-1] > rsi_values[-2] + 1.5):
            strategy = "🚀 تدفق سيولة"
            risk_level = "مرتفع"
        
        else:
            return None
        
        # حساب أهداف ديناميكية
        targets = calculate_dynamic_targets(price, highs, lows, closes, rsi, volume_ratio)
        
        # بناء الرسالة
        msg = (
            f"<b>{strategy}</b> | {risk_level} ⚠️\n\n"
            f"🪙 <b>{symbol}</b>\n"
            f"💰 السعر: <code>{price:.6f}</code>\n"
            f"📊 RSI: {rsi:.1f} | EMA20/50: {ema20:.6f}/{ema50:.6f}\n"
            f"🔥 حجم: {volume_ratio:.1f}x | الحركة: {move_pct:+.2f}%\n"
            f"⏱️ الكشف: <b>{datetime.now().strftime('%H:%M:%S')}</b>\n\n"
            f"🎯 TP1: {targets['tp1']:.6f} (+{targets['tp1_pct']}%)\n"
            f"🎯 TP2: {targets['tp2']:.6f} (+{targets['tp2_pct']}%)\n"
        )
        
        if targets['tp3']:
            msg += f"🎯 TP3: {targets['tp3']:.6f} (+{targets['tp3_pct']}%)\n"
        
        msg += (
            f"🛑 SL: {targets['sl']:.6f} (-{targets['sl_pct']}%)\n\n"
            f"💡 <i>التحليل: كسر حديث لمقاومة مع تدفق سيولة أولي - المرحلة المبكرة من الصعود</i>"
        )
        
        return msg
        
    except Exception as e:
        print(f"تحليل {symbol} خطأ: {str(e)[:80]}")
        return None

# ================== الماسح الرئيسي ==================
def run_scanner():
    print("🚀 صياد الحركات المبكرة - بدء التشغيل...")
    send_telegram("✅ صياد الحركات المبكرة نشط!\n🎯 يركز على العملات في أول 15-30 دقيقة من الصعود")
    
    cycle = 0
    while True:
        cycle += 1
        try:
            print(f"\n[{cycle}] بدء دورة المسح...")
            
            # جلب أفضل 150 عملة حجماً
            tickers = requests.get(f"{BASE}/ticker/24hr", timeout=10).json()
            usdt_pairs = [
                t for t in tickers 
                if t["symbol"].endswith("USDT") 
                and float(t.get("quoteVolume", 0)) > 30000000
                and not any(x in t["symbol"] for x in ["UP", "DOWN", "BULL", "BEAR"])
            ]
            usdt_pairs.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)
            symbols = [t["symbol"] for t in usdt_pairs[:150]]
            
            print(f"✓ جاري تحليل {len(symbols)} عملة عالية الحجم...")
            
            signals_found = 0
            for symbol in symbols:
                # تجنب التكرار
                if symbol in SENT_ALERTS and time.time() - SENT_ALERTS[symbol] < MIN_ALERT_INTERVAL:
                    continue
                
                # جلب البيانات
                try:
                    klines = requests.get(
                        f"{BASE}/klines",
                        params={"symbol": symbol, "interval": "5m", "limit": 80},
                        timeout=8
                    ).json()
                    
                    if len(klines) < 70:
                        continue
                    
                    signal = analyze_symbol(symbol, klines)
                    
                    if signal:
                        # إرسال الإشارة فقط إذا نجحت
                        if send_telegram(signal, symbol):
                            SENT_ALERTS[symbol] = time.time()
                            signals_found += 1
                            print(f"✨ إشارة جديدة: {symbol}")
                        
                        # تأخير أقصر بعد إشارة
                        time.sleep(0.3)
                    else:
                        time.sleep(0.08)
                
                except Exception as e:
                    time.sleep(0.1)
                    continue
            
            print(f"✓ اكتملت الدورة - وُجدت {signals_found} إشارات")
            
            # إرسال تقرير كل ساعة
            if cycle % 12 == 0:
                active = len([t for t in SENT_ALERTS.values() if time.time() - t < 3600])
                send_telegram(f"📊 تقرير الساعة:\n- إشارات نشطة: {active}\n- العملات الممسوحة: {len(symbols)}/دورة")
            
            time.sleep(4.5)
            
        except Exception as e:
            print(f"❌ خطأ في الماسح: {str(e)[:100]}")
            time.sleep(10)

# ================== التشغيل ==================
if __name__ == "__main__":
    print("="*50)
    print(" صياد الحركات المبكرة - الإصدار المتطور")
    print("🎯 الهدف: اكتشاف العملات في أول 15-30 دقيقة من الصعود")
    print("⚡ 3 استراتيجيات: سكالبينج | ترند | تدفق سيولة")
    print("🎯 أهداف ديناميكية تعتمد على التحليل (ليست ثابتة)")
    print("="*50)
    
    # ⚠️ تحذير أمان فوري
    if "YOUR_BOT_TOKEN" in BOT_TOKEN or "YOUR_CHAT_ID" in CHAT_ID:
        print("\n⚠️  تحذير: توكن التلغرام أو الـ Chat ID غير مُعدّل! غيّره فوراً")
        print("1. اذهب إلى @BotFather وأنشئ توكن جديد")
        print("2. استخدم توكنك الجديد مكان 'YOUR_BOT_TOKEN_HERE'")
        print("3. استخدم رقم محادثتك مكان 'YOUR_CHAT_ID_HERE'")
        print("4. أرسل /start للبوت قبل التشغيل")
        print("="*50)
    
    # اختبار اتصال تلغرام قبل التشغيل
    print("\n🧪 اختبار اتصال تلغرام...")
    test_sent = send_telegram("✅ اختبار اتصال ناجح - الصياد جاهز!")
    
    if test_sent:
        print("✅ جاهز للتشغيل - انتظر الإشارات...")
        run_scanner()
    else:
        print("❌ فشل اختبار التلغرام - تحقق من التوكن والـ Chat ID")
        print("💡 اضغط Ctrl+C لإنهاء البرنامج")
        while True:
            time.sleep(1)
