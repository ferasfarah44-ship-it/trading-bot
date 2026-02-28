import os
import time
import requests

print("🚀 BOT STARTED - REAL 15m CHECK")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Missing Telegram variables")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def get_closed_candle(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=2"
    r = requests.get(url, timeout=10)
    data = r.json()

    if not isinstance(data, list) or len(data) < 2:
        return None

    last = data[-1]

    # وقت إغلاق الشمعة
    close_time = last[6] / 1000
    current_time = time.time()

    # إذا انتهت فعلاً
    if current_time >= close_time:
        open_price = float(last[1])
        close_price = float(last[4])
        return open_price, close_price

    return None

def run():
    send_telegram("Bot running - real closed 15m candles")

    while True:
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=15)
            data = r.json()

            usdt_pairs = [x for x in data if x['symbol'].endswith("USDT")]
            usdt_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
            top_pairs = usdt_pairs[:100]

            for coin in top_pairs:
                s = coin['symbol']
                candle = get_closed_candle(s)
                if candle is None:
                    continue

                open_price, close_price = candle
                change = ((close_price - open_price) / open_price) * 100

                if change >= 0.5:
                    send_telegram(f"🚀 {s} +{change:.2f}% (15m closed)")
                    time.sleep(0.2)

            print("Cycle done")
            time.sleep(60)

        except Exception as e:
            print("Error:", e)
            time.sleep(30)

if __name__ == "__main__":
    run()
