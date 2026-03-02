import os
import time
import requests
import pandas as pd
import pandas_ta as ta

# جلب الإعدادات من Railway Variables
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOLS = ['SOLUSDT', 'ETHUSDT', 'OPUSDT', 'NEARUSDT', 'ARBUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT']

def send_msg(text):
    """إرسال رسالة تليجرام عبر رابط مباشر لضمان العمل"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload)
        print(f"Telegram Response: {r.status_code}") # سيظهر في Logs التابع لـ Railway
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

def get_market_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def analyze():
    print("جاري فحص العملات...")
    for symbol in SYMBOLS:
        try:
            df = get_market_data(symbol)
            # مؤشرات بسيطة وقوية
            df['RSI'] = ta.rsi(df['close'], length=14)
            df['EMA7'] = ta.ema(df['close'], length=7)
            df['EMA25'] = ta.ema(df['close'], length=25)
            
            last_close = df['close'].iloc[-1]
            last_rsi = df['RSI'].iloc[-1]
            ema7 = df['EMA7'].iloc[-1]
            ema25 = df['EMA25'].iloc[-1]

            # شرط دخول "مطمئن": السعر فوق المتوسطات + زخم شراء
            if last_close > ema7 and ema7 > ema25 and last_rsi > 55:
                msg = (f"🚀 **فرصة صعود: {symbol}**\n"
                       f"💰 السعر الحالي: `{last_close}`\n"
                       f"🔥 القوة (RSI): `{last_rsi:.2f}`\n"
                       f"🎯 هدف (3%): `{last_close * 1.03:.4f}`")
                send_msg(msg)
        except Exception as e:
            print(f"خطأ في تحليل {symbol}: {e}")

# عند التشغيل لأول مرة
send_msg("🤖 تم تشغيل البوت بنجاح.. جاري مراقبة السوق.")
last_heartbeat = time.time()

while True:
    analyze()
    
    # رسالة كل ساعة للتأكد
    if time.time() - last_heartbeat > 3600:
        send_msg("✅ تحديث: البوت لا يزال يعمل ويحلل العملات.")
        last_heartbeat = time.time()
    
    time.sleep(300) # فحص كل 5 دقائق لضمان استقرار السيرفر
