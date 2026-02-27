import os
import time
import requests
import pandas as pd

print("🚀 BOT STARTED - 2% CANDLE MODE")

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

def get_last_candle(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=2"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) >= 1:
            last = data[-1]
            open_price = float(last[1])
            close_price = float(last[4])
            return open_price, close_price
    except:
        return None

def run():
    send_telegram("📡 Bot running - catching 2% 15m candles")

    while True:
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price")
            tickers = r.json()

            if isinstance(tickers, list):
                symbols = [t['symbol'] for t in tickers if t['symbol'].endswith("USDT")]

                for s in symbols:
                    candle = get_last_candle(s)
                    if candle is None:
                        continue

                    open_price, close_price = candle
                    change_percent = ((close_price - open_price) / open_price) * 100

                    # 🔥 الشرط الجديد: 2% صعود خلال 15 دقيقة
                    if change_percent >= 2:
                        msg = (
                            f"🚀 Strong 15m Move\n"
                            f"{s}\n"
                            f"Change: {change_percent:.2f}%\n"
                            f"Price: {close_price}"
                        )
                        send_telegram(msg)
                        time.sleep(0.3)

            print("Cycle done")
            time.sleep(600)

        except Exception as e:
            print("Loop Error:", e)
            time.sleep(60)

if __name__ == "__main__":
    run()
