import os
import time
import requests
import pandas as pd

# المتغيرات من Railway
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_msg(text):
    url = f"https://api.telegram.org{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except:
        return False

def get_data(symbol):
    # جلب شمعات الـ 15 دقيقة (نفس إطار الصورة)
    url = f"https://api.binance.com{symbol}&interval=15m&limit=100"
    try:
        resp = requests.get(url, timeout=10).json()
        df = pd.DataFrame(resp).iloc[:, :6]
        df.columns = ['time', 'open', 'high', 'low', 'close', 'vol']
        df['close'] = pd.to_numeric(df['close'])
        return df
    except:
        return None

def start_engine():
    # 1. رسالة فورية عند بدء التشغيل
    print(">>> Sending Startup Message...")
    if send_msg("✅ **تم تشغيل البوت بنجاح!**\nبدأت الآن مراقبة سوق USDT."):
        print(">>> Startup Message Sent!")
    else:
        print(">>> Failed to send startup message. Check Token/ID.")

    last_hourly = time.time()

    while True:
        try:
            # 2. رسالة تأكيد العمل كل ساعة
            if time.time() - last_hourly >= 3600:
                send_msg("🔔 **تنبيه:** البوت يعمل بنجاح ويحلل العملات الآن.")
                last_hourly = time.time()
                print(">>> Hourly status sent.")

            # جلب أسعار العملات
            prices = requests.get("https://api.binance.com").json()
            symbols = [t['symbol'] for t in prices if t['symbol'].endswith('USDT')]

            print(f">>> Analyzing {len(symbols[:100])} symbols...")
            
            for s in symbols[:100]: # تحليل أفضل 100 عملة لضمان السرعة
                df = get_data(s)
                if df is None or len(df) < 30: continue

                # حساب المتوسطات (الخط الأصفر MA7)
                df['MA7'] = df['close'].rolling(window=7).mean()
                df['MA25'] = df['close'].rolling(window=25).mean()

                # 3. شرط الفرصة (التقاطع الصعودي للخط الأصفر)
                if df['MA7'].iloc[-1] > df['MA25'].iloc[-1] and df['MA7'].iloc[-2] <= df['MA25'].iloc[-2]:
                    p = df['close'].iloc[-1]
                    msg = (f"🚀 **فرصة صعود: {s}**\n"
                           f"💰 السعر: `{p}`\n"
                           f"🎯 هدف 1: `{p * 1.02:.4f}`\n"
                           f"🎯 هدف 2: `{p * 1.05:.4f}`\n"
                           f"🛑 وقف: `{p * 0.97:.4f}`")
                    send_msg(msg)
                    print(f">>> Signal sent for {s}")
                    time.sleep(1)

            print(">>> Cycle complete. Waiting 10 minutes...")
            time.sleep(600) # انتظار 10 دقائق قبل الدورة التالية
            
        except Exception as e:
            print(f">>> Error in loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_engine()
