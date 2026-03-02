import os
import time
import requests

# الإعدادات
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOLS = ['SOLUSDT', 'ETHUSDT', 'OPUSDT', 'NEARUSDT', 'ARBUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT']

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except:
        pass

def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    return float(requests.get(url).json()['price'])

def analyze():
    # تحليل سريع: إذا كان السعر الحالي أعلى من سعر قبل 5 دقائق
    for symbol in SYMBOLS:
        try:
            p1 = get_price(symbol)
            time.sleep(2) # انتظار بسيط
            p2 = get_price(symbol)
            
            if p2 > p1: # منطق صعود بسيط جداً للتأكد من العمل
                send_msg(f"📈 العملة: {symbol}\n💰 السعر: {p2}")
        except:
            continue

# رسالة عند التشغيل فوراً
send_msg("🚀 البوت بدأ العمل الآن على Railway")

while True:
    analyze()
    time.sleep(300) # فحص كل 5 دقائق
