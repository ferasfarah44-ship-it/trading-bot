import os
import time
import requests
import pandas as pd

# قراءة المتغيرات من Railway
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("!!! ERROR: TOKEN or CHAT_ID is missing in Railway Variables !!!")
        return False
    url = f"https://api.telegram.org{TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)
        return r.status_code == 200
    except:
        return False

def get_data(symbol):
    url = f"https://api.binance.com{symbol}&interval=15m&limit=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list): # التأكد أن الرد قائمة لمنع الخطأ الظاهر في الصورة
            df = pd.DataFrame(data).iloc[:, :6]
            df.columns = ['time', 'open', 'high', 'low', 'close', 'vol']
            df['close'] = pd.to_numeric(df['close'])
            return df
    except:
        return None

def start_bot():
    print(">>> Attempting to send start message...")
    if send_telegram("🚀 **تم تشغيل البوت بنجاح!**\nبدأ تحليل سوق USDT بالكامل."):
        print(">>> START MESSAGE SENT!")
    
    last_hourly = time.time()

    while True:
        try:
            if time.time() - last_hourly >= 3600:
                send_telegram("🔔 **تحديث الساعة:** البوت يعمل ويحلل السوق.")
                last_hourly = time.time()

            # جلب العملات
            r = requests.get("https://api.binance.com")
            tickers = r.json()
            
            # التأكد من جلب البيانات بشكل صحيح لتجنب خطأ string indices
            if isinstance(tickers, list):
                symbols = [t['symbol'] for t in tickers if t['symbol'].endswith('USDT')]
                
                for s in symbols:
                    df = get_data(s)
                    if df is None or len(df) < 30: continue

                    # التحليل (الخط الأصفر MA7)
                    df['MA7'] = df['close'].rolling(window=7).mean()
                    df['MA25'] = df['close'].rolling(window=25).mean()

                    if df['MA7'].iloc[-1] > df['MA25'].iloc[-1] and df['MA7'].iloc[-2] <= df['MA25'].iloc[-2]:
                        p = df['close'].iloc[-1]
                        msg = (f"📈 **فرصة دخول: {s}**\n💰 السعر: `{p}`\n🎯 هدف: `{p * 1.02:.4f}`\n🛑 وقف: `{p * 0.97:.4f}`")
                        send_telegram(msg)
                        time.sleep(1)

            time.sleep(600)
        except Exception as e:
            print(f">>> Loop Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_bot()
