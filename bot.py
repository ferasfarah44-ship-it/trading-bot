import os
import time
import requests
import pandas as pd

print("🚀 BOT STARTED SUCCESSFULLY")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("❌ TELEGRAM VARIABLES MISSING")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

def get_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=50"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if isinstance(data, list) and len(data) > 10:
            df = pd.DataFrame(data).iloc[:, :6]
            df.columns = ['time','open','high','low','close','vol']
            df['close'] = pd.to_numeric(df['close'])
            return df
    except:
        return None

def run():
    send_telegram("🤖 Bot is running (MA7 rising only)")

    while True:
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price")
            tickers = r.json()

            if isinstance(tickers, list):
                symbols = [t['symbol'] for t in tickers if t['symbol'].endswith("USDT")]

                for s in symbols:
                    df = get_data(s)
                    if df is None:
                        continue

                    df['MA7'] = df['close'].rolling(7).mean()

                    curr = df['MA7'].iloc[-1]
                    prev = df['MA7'].iloc[-2]

                    # 🔥 الشرط الوحيد: أي ارتفاع للأصفر
                    if curr > prev:
                        price = df['close'].iloc[-1]
                        msg = f"📈 MA7 Rising\n{ s }\nPrice: { price }"
                        send_telegram(msg)
                        time.sleep(0.3)

            print("Cycle done")
            time.sleep(600)

        except Exception as e:
            print("Loop Error:", e)
            time.sleep(60)

if __name__ == "__main__":
    run()
