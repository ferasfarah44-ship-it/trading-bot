import os
import time
import requests
import pandas as pd
import pandas_ta as ta

# الإعدادات من Railway (Variables)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOLS = ['SOLUSDT', 'ETHUSDT', 'OPUSDT', 'NEARUSDT', 'ARBUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT']

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    res = requests.get(url).json()
    df = pd.DataFrame(res, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def check_market():
    for symbol in SYMBOLS:
        try:
            df = get_data(symbol)
            df['RSI'] = ta.rsi(df['close'], length=14)
            df['MA7'] = ta.sma(df['close'], length=7)
            df['MA25'] = ta.sma(df['close'], length=25)
            
            cp = df['close'].iloc[-1]
            rsi = df['RSI'].iloc[-1]
            ma7 = df['MA7'].iloc[-1]
            ma25 = df['MA25'].iloc[-1]

            # شرط الدخول (سعر صاعد + زخم)
            if cp > ma7 and ma7 > ma25 and rsi > 55:
                msg = (f"🚀 **فرصة دخول قوية: {symbol}**\n"
                       f"💰 السعر: `{cp:.4f}`\n"
                       f"🔥 القوة (RSI): `{rsi:.2f}`\n"
                       f"🎯 هدف (3%): `{cp*1.03:.4f}`")
                send_telegram_msg(msg)
        except:
            continue

# بداية التشغيل
send_telegram_msg("✅ تم تشغيل البوت بنجاح على Railway")
last_health = time.time()

while True:
    check_market()
    
    # رسالة التأكد كل ساعة
    if time.time() - last_health > 3600:
        send_telegram_msg("🟢 تحديث: البوت يعمل ويحلل الآن..")
        last_health = time.time()
    
    time.sleep(300) # فحص كل 5 دقائق لضمان عدم الحظر
