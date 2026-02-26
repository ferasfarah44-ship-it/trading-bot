import os
import time
import requests
import pandas as pd

# إعدادات التليجرام من Railway Settings -> Variables
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_msg(text):
    url = f"https://api.telegram.org{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def get_binance_data(symbol):
    # جلب بيانات الشموع مباشرة من API بينانس العام
    url = f"https://api.binance.com{symbol}&interval=15m&limit=100"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'q_vol', 'trades', 'takers_buy_base', 'takers_buy_quote', 'ignore'])
        df['close'] = pd.to_numeric(df['close'])
        return df
    except:
        return None

def run_bot():
    send_msg("🚀 **تم تشغيل البوت بنجاح!** بدأ تحليل سوق USDT الآن.")
    last_ping = time.time()

    while True:
        try:
            # رسالة تأكيد العمل كل ساعة
            if time.time() - last_ping >= 3600:
                send_msg("⏰ **تنبيه ساعة:** البوت مستمر في مراقبة السوق.")
                last_ping = time.time()

            # جلب قائمة العملات
            all_tickers = requests.get("https://api.binance.com").json()
            symbols = [t['symbol'] for t in all_tickers if t['symbol'].endswith('USDT')]

            for s in symbols[:150]: # تحليل أهم 150 عملة لتجنب الحظر
                df = get_binance_data(s)
                if df is None or len(df) < 30: continue

                # حساب المتوسطات (الخط الأصفر MA7)
                df['MA7'] = df['close'].rolling(window=7).mean()
                df['MA25'] = df['close'].rolling(window=25).mean()

                # شرط التقاطع الصعودي
                if df['MA7'].iloc[-1] > df['MA25'].iloc[-1] and df['MA7'].iloc[-2] <= df['MA25'].iloc[-2]:
                    price = df['close'].iloc[-1]
                    msg = (f"📈 **فرصة دخول: {s}**\n"
                           f"💰 السعر الحالي: {price}\n"
                           f"🎯 هدف 1 (2%): {price * 1.02:.4f}\n"
                           f"🎯 هدف 2 (5%): {price * 1.05:.4f}\n"
                           f"🛑 وقف الخسارة: {price * 0.97:.4f}")
                    send_msg(msg)
                    time.sleep(1) # تأخير بسيط بين الرسائل

            time.sleep(900) # فحص جديد كل 15 دقيقة
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
