import os
import time
import requests
import pandas as pd

# جلب المتغيرات - تأكد من كتابتها CAPITAL في Railway
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("!!! ERROR: TOKEN or CHAT_ID is missing in Railway Variables !!!")
        return False
    url = f"https://api.telegram.org{TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=15)
        print(f">>> Telegram Response: {r.status_code} - {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f">>> Telegram Connection Error: {e}")
        return False

def get_binance_data(symbol):
    url = f"https://api.binance.com{symbol}&interval=15m&limit=50"
    try:
        response = requests.get(url, timeout=10).json()
        df = pd.DataFrame(response).iloc[:, :6]
        df.columns = ['time', 'open', 'high', 'low', 'close', 'vol']
        df['close'] = pd.to_numeric(df['close'])
        return df
    except:
        return None

def start_process():
    # الخطوة 1: إرسال رسالة فورية عند التشغيل (قبل أي شيء آخر)
    print(">>> Attempting to send start message...")
    status = send_telegram("🚀 **تم تشغيل البوت بنجاح!**\nجاري البدء في تحليل سوق USDT بالكامل.")
    
    if not status:
        print("!!! FAILED TO SEND START MESSAGE - Check your Token/ID again !!!")

    last_hourly_msg = time.time()

    while True:
        try:
            # رسالة كل ساعة
            if time.time() - last_hourly_msg >= 3600:
                send_telegram("🔔 **تحديث:** البوت يعمل ويحلل السوق الآن.")
                last_hourly_msg = time.time()

            # جلب كل عملات USDT (أكثر من 400 عملة)
            all_tickers = requests.get("https://api.binance.com").json()
            symbols = [t['symbol'] for t in all_tickers if t['symbol'].endswith('USDT')]

            print(f">>> Scanning {len(symbols)} symbols...")
            
            for s in symbols:
                df = get_binance_data(s)
                if df is None or len(df) < 30: continue

                # التحليل الفني (الخط الأصفر MA7)
                df['MA7'] = df['close'].rolling(window=7).mean()
                df['MA25'] = df['close'].rolling(window=25).mean()

                # شرط الإشارة
                if df['MA7'].iloc[-1] > df['MA25'].iloc[-1] and df['MA7'].iloc[-2] <= df['MA25'].iloc[-2]:
                    price = df['close'].iloc[-1]
                    msg = (f"📈 **إشارة دخول: {s}**\n"
                           f"💰 السعر: `{price}`\n"
                           f"🎯 هدف 1 (2%): `{price * 1.02:.4f}`\n"
                           f"🎯 هدف 2 (5%): `{price * 1.05:.4f}`\n"
                           f"🛑 وقف الخسارة: `{price * 0.97:.4f}`")
                    send_telegram(msg)
                    time.sleep(1) # تأخير لتجنب السبام

            print(">>> Cycle finished. Waiting 10 mins...")
            time.sleep(600)
            
        except Exception as e:
            print(f">>> Loop Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_process()
