import os
import time
import requests
import pandas as pd

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("TOKEN or CHAT_ID missing")
        return False
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    try:
        r = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text},
            timeout=15
        )
        return r.status_code == 200
    except:
        return False

def get_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
    
    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if isinstance(data, list) and len(data) > 30:
            df = pd.DataFrame(data).iloc[:, :6]
            df.columns = ['time', 'open', 'high', 'low', 'close', 'vol']
            df['close'] = pd.to_numeric(df['close'])
            return df
    except:
        return None

def start_bot():
    send_telegram("🚀 تم تشغيل بوت ميل MA7 فقط (15م)")
    
    while True:
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price")
            tickers = r.json()

            if isinstance(tickers, list):
                symbols = [t['symbol'] for t in tickers if t['symbol'].endswith('USDT')]

                for s in symbols:
                    df = get_data(s)
                    if df is None:
                        continue

                    df['MA7'] = df['close'].rolling(7).mean()

                    curr = df['MA7'].iloc[-1]
                    prev = df['MA7'].iloc[-2]

                    # 🔥 الشرط الوحيد: أي ارتفاع
                    if curr > prev:
                        price = df['close'].iloc[-1]

                        msg = (
                            f"📈 MA7 صاعد\n"
                            f"العملة: {s}\n"
                            f"السعر: {price}"
                        )

                        send_telegram(msg)
                        time.sleep(0.5)

            print("Cycle done - waiting 10 min")
            time.sleep(600)

        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_bot()
