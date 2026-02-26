import os
import time
import requests
import pandas as pd

# تأكد أن هذه الأسماء مطابقة تماماً لما كتبته في Railway Variables
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("خطأ: لم يتم العثور على TELEGRAM_TOKEN أو TELEGRAM_CHAT_ID في الإعدادات!")
        return
    
    url = f"https://api.telegram.org{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print(f"خطأ من تليجرام: {r.text}")
    except Exception as e:
        print(f"فشل الاتصال بتليجرام: {e}")

def get_data(symbol):
    url = f"https://api.binance.com{symbol}&interval=15m&limit=100"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data)
        df = df.iloc[:, :6]
        df.columns = ['time', 'open', 'high', 'low', 'close', 'vol']
        df['close'] = pd.to_numeric(df['close'])
        return df
    except:
        return None

def start_bot():
    # 1. رسالة عند بدء التشغيل فوراً
    print("جاري إرسال رسالة البدء...")
    send_msg("✅ **تم تشغيل البوت بنجاح!**\nسأقوم الآن بتحليل سوق USDT وإرسال تنبيه كل ساعة وعند توفر فرص.")
    
    last_hourly_msg = time.time()

    while True:
        try:
            # 2. رسالة كل ساعة للتأكد من عمل الكود
            if time.time() - last_hourly_msg >= 3600:
                send_msg("🔔 **تحديث الساعة:** البوت يعمل بنجاح ويحلل السوق حالياً.")
                last_hourly_msg = time.time()

            # جلب قائمة العملات
            r = requests.get("https://api.binance.com")
            all_symbols = [t['symbol'] for t in r.json() if t['symbol'].endswith('USDT')]

            for s in all_symbols[:100]: # تحليل أفضل 100 عملة لسرعة الأداء
                df = get_data(s)
                if df is None or len(df) < 30: continue

                # حساب المتوسطات (الخط الأصفر MA7)
                df['MA7'] = df['close'].rolling(window=7).mean()
                df['MA25'] = df['close'].rolling(window=25).mean()

                # 3. إرسال رسالة عند وجود فرصة (تقاطع صعودي)
                if df['MA7'].iloc[-1] > df['MA25'].iloc[-1] and df['MA7'].iloc[-2] <= df['MA25'].iloc[-2]:
                    price = df['close'].iloc[-1]
                    signal = (f"📈 **فرصة دخول لعملة: {s}**\n"
                              f"💰 السعر الحالي: `{price}`\n"
                              f"🎯 هدف 1: `{price * 1.02:.4f}`\n"
                              f"🎯 هدف 2: `{price * 1.05:.4f}`\n"
                              f"🛑 وقف الخسارة: `{price * 0.97:.4f}`")
                    send_msg(signal)
                    time.sleep(2)

            time.sleep(600) # فحص شامل كل 10 دقائق
        except Exception as e:
            print(f"حدث خطأ في الدورة: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_bot()
