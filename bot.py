import requests
import time
import statistics

# ================= الإعدادات الأساسية =================
BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

SENT_ALERTS = {}
LAST_HEARTBEAT = time.time()
BOT_STATUS = "تشغيل تلقائي 🟢"

# ================= وظائف الاتصال والرسائل =================

def send_telegram(msg, symbol=None, is_alert=False):
    """إرسال رسالة مع أزرار التحكم أو أزرار العملة"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        # لوحة التحكم الأساسية (تظهر مع رسائل الاطمئنان)
        main_keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 فحص الآن", "callback_data": "scan"}, {"text": "🛑 إيقاف", "callback_data": "stop"}],
                [{"text": "🟢 تشغيل تلقائي", "callback_data": "start"}]
            ]
        }

        # لوحة أزرار العملة (تظهر عند وجود فرصة)
        if symbol:
            currency_keyboard = {
                "inline_keyboard": [
                    [{"text": "📊 فتح الشارت (Binance)", "url": f"https://www.binance.com/en/trade/{symbol}"}],
                    [{"text": "🔍 الاستفسار عن الحكم الشرعي", "url": f"https://cryptohalal.net/search?q={symbol.replace('USDT', '')}"}]
                ]
            }
            keyboard = currency_keyboard
        else:
            keyboard = main_keyboard

        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
            "disable_notification": False if is_alert else True # صوت عند التنبيهات فقط
        }
        
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# ================= الوظائف الفنية =================

def calculate_rsi(prices, period=14):
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
    if len(prices) < period: return prices[-1]
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def get_signal(sym):
    try:
        params = {"symbol": sym, "interval": "5m", "limit": 50}
        r = requests.get(f"{BASE}/klines", params=params, timeout=10)
        if r.status_code != 200: return None
        k5 = r.json()
        closes = [float(k[4]) for k in k5]
        vols = [float(k[5]) for k in k5]
        current_price = closes[-1]
        open_price = float(k5[-1][1])
        vol_now = vols[-1]
        vol_avg = statistics.mean(vols[-20:-1])
        
        rsi_val = calculate_rsi(closes)
        ema_val = calculate_ema(closes)
        
        # شروط الدخول
        if vol_now > vol_avg * 2.2 and current_price > open_price and current_price > ema_val and rsi_val < 72:
            entry = current_price
            tp1, tp2, sl = entry * 1.015, entry * 1.030, entry * 0.980
            
            return (f"🚀 **فرصة دخول جديدة**\n\n"
                    f"🪙 العملة: #{sym}\n"
                    f"💰 الدخول: `{entry:.6f}`\n"
                    f"📈 القوة (RSI): {rsi_val:.2f}\n\n"
                    f"🎯 أهدافك: `{tp1:.6f}` | `{tp2:.6f}`\n"
                    f"🚫 الوقف: `{sl:.6f}`")
        return None
    except:
        return None

# ================= الدورة التشغيلية =================

def run_scanner():
    global LAST_HEARTBEAT
    send_telegram(f"🛰️ **تم بدء تشغيل الرادار بنجاح**\nالحالة الحالية: {BOT_STATUS}")
    
    while True:
        # رسالة الاطمئنان كل ساعة
        if time.time() - LAST_HEARTBEAT >= 3600:
            send_telegram("✅ **تم فحص العملات الرقمية بنجاح.**\nلا توجد فرص محققة في هذه الساعة.")
            LAST_HEARTBEAT = time.time()

        try:
            r = requests.get(f"{BASE}/exchangeInfo", timeout=10).json()
            symbols = [s['symbol'] for s in r['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
            
            for symbol in symbols:
                signal = get_signal(symbol)
                if signal:
                    now = time.time()
                    if symbol not in SENT_ALERTS or (now - SENT_ALERTS[symbol] > 7200):
                        send_telegram(signal, symbol=symbol, is_alert=True)
                        SENT_ALERTS[symbol] = now
                time.sleep(0.05) # سرعة فحص عالية مع حماية IP
        except:
            time.sleep(10)
        
        time.sleep(5)

if __name__ == "__main__":
    run_scanner()
