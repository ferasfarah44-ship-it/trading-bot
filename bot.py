import time
import requests
import pandas as pd
import pandas_ta as ta

# --- ضع بياناتك هنا ---
TELEGRAM_TOKEN = "7864353229:AAGF1r8N..." # ضع التوكن بالكامل هنا
CHAT_ID = "634814..." # ضع الآيدي هنا
# ----------------------

SYMBOLS = ['SOLUSDT', 'ETHUSDT', 'OPUSDT', 'NEARUSDT', 'ARBUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT']

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except:
        print("تعذر إرسال تليجرام")

def analyze():
    print(f"\n--- فحص: {time.strftime('%H:%M:%S')} ---")
    for symbol in SYMBOLS:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
            res = requests.get(url).json()
            df = pd.DataFrame(res, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
            df['close'] = df['close'].astype(float)
            
            # المؤشرات
            df['EMA7'] = ta.ema(df['close'], length=7)
            df['EMA25'] = ta.ema(df['close'], length=25)
            df['RSI'] = ta.rsi(df['close'], length=14)
            
            cp = df['close'].iloc[-1]
            e7 = df['EMA7'].iloc[-1]
            e25 = df['EMA25'].iloc[-1]
            rsi = df['RSI'].iloc[-1]

            print(f"[{symbol}] السعر: {cp} | RSI: {rsi:.2f}")

            # شرط الدخول الذهبي: تقاطع EMA7 فوق EMA25 + RSI فوق 50
            if cp > e7 and e7 > e25 and rsi > 50:
                msg = (f"🚀 **إشارة دخول: {symbol}**\n"
                       f"💰 السعر: `{cp}`\n"
                       f"🔥 القوة: `{rsi:.2f}`\n"
                       f"🎯 هدف (3%): `{cp*1.03:.4f}`")
                send_msg(msg)
        except Exception as e:
            print(f"خطأ في {symbol}: {e}")

# بداية التشغيل
send_msg("🤖 البوت بدأ العمل على Pydroid بنجاح!")
while True:
    analyze()
    time.sleep(300) # فحص كل 5 دقائق
