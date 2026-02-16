import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime

# ====================================================
# الإعدادات - ضع بياناتك هنا
# ====================================================
TELEGRAM_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"

# تهيئة الاتصال بباينانس مع حماية من الحظر (Rate Limit)
exchange = ccxt.binance({'enableRateLimit': True})

def send_telegram_msg(message):
    """إرسال رسائل نصية عبر بوت تليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ خطأ في إرسال تليجرام: {e}")

def get_all_usdt_symbols():
    """جلب جميع أزواج USDT النشطة في باينانس"""
    try:
        exchange.load_markets()
        return [s for s in exchange.symbols if '/USDT' in s and exchange.markets[s]['active']]
    except Exception as e:
        print(f"❌ خطأ في جلب العملات: {e}")
        return []

def analyze_logic(symbol):
    """المنطق البرمجي لتحليل العملة واستخراج الأهداف"""
    try:
        # جلب آخر 100 شمعة (إطار الساعة يعطي توازن بين السرعة والدقة)
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات الفنية باستخدام pandas_ta
        df['RSI'] = df.ta.rsi(length=14)
        df['ATR'] = df.ta.atr(length=14)
        bb = df.ta.bbands(length=20, std=2)
        df = pd.concat([df, bb], axis=1)

        # بيانات آخر شمعة مكتملة
        last = df.iloc[-1]
        price = last['close']
        upper_band = last['BBU_20_2.0']
        rsi = last['RSI']
        atr = last['ATR']

        # --- شرط الانفجار السعري ---
        if price > upper_band and rsi > 60:
            # حساب الأهداف بناءً على تذبذب العملة (ATR)
            sl = price - (atr * 1.5)      # وقف الخسارة
            tp1 = price + (atr * 1.5)     # الهدف الأول
            tp2 = price + (atr * 3.0)     # الهدف الثاني (طموح)

            return (
                f"🚀 *إشارة انفجار سعري: {symbol}*\n\n"
                f"💰 سعر الدخول الحقيقي: {price:.5f}\n"
                f"🎯 الهدف الأول: {tp1:.5f}\n"
                f"🔥 الهدف الثاني: {tp2:.5f}\n"
                f"🛡️ وقف الخسارة: {sl:.5f}\n\n"
                f"📈 مؤشر RSI: {rsi:.2f}\n"
                f"⏰ التوقيت: {datetime.now().strftime('%H:%M')}"
            )
    except:
        return None
    return None

# ====================================================
# الحلقة الرئيسية (التشغيل المستمر)
# ====================================================
print("🤖 البوت بدأ العمل... سيتم إرسال رسالة تليجرام كل ساعة.")

while True:
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. رسالة التأكيد (التي طلبتها كل ساعة)
    heartbeat_msg = f"✅ *تحديث الحالة:* الكود يعمل بنجاح.\n📅 التاريخ: {start_time}\n🔍 جاري مسح جميع أسواق USDT حالياً..."
    send_telegram_msg(heartbeat_msg)
    
    # 2. عملية المسح والتحليل
    all_pairs = get_all_usdt_symbols()
    found_count = 0
    
    for pair in all_pairs:
        # تجنب العملات التي سعرها ضئيل جداً أو الـ Stablecoins
        if 'UP/' in pair or 'DOWN/' in pair or 'DAI/' in pair: continue
        
        signal = analyze_logic(pair)
        if signal:
            send_telegram_msg(signal)
            found_count += 1
        
        # تأخير بسيط جداً (0.05 ثانية) لضمان عدم الضغط على الـ API
        time.sleep(0.05)
    
    print(f"🏁 انتهى المسح في {datetime.now()}. الإشارات المرسلة: {found_count}")
    
    # 3. الانتظار لمدة ساعة (3600 ثانية) قبل تكرار الدورة
    time.sleep(3600)
