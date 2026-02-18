import os
import time
import requests
from datetime import datetime

# =========================
# LOAD ENV VARIABLES
# =========================

TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
TELEGRAM_CHAT_ID = os.getenv("7960335113")

print("Loaded TOKEN:", TELEGRAM_TOKEN is not None)
print("Loaded CHAT_ID:", TELEGRAM_CHAT_ID is not None)

# =========================
# TELEGRAM FUNCTION
# =========================

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

# =========================
# BINANCE DATA
# =========================

def get_usdt_pairs():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    data = requests.get(url).json()

    symbols = []
    for s in data["symbols"]:
        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING":
            symbols.append(s["symbol"])

    return symbols[:150]   # 150 عملة

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
    return requests.get(url).json()

# =========================
# SIMPLE BREAKOUT LOGIC
# =========================

def check_signal(symbol):
    klines = get_klines(symbol)

    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    last_close = closes[-1]
    prev_high = max(closes[-10:-1])
    avg_volume = sum(volumes[-20:-1]) / 19
    last_volume = volumes[-1]

    if last_close > prev_high and last_volume > avg_volume * 1.5:
        entry = last_close
        tp1 = round(entry * 1.02, 6)
        tp2 = round(entry * 1.04, 6)
        tp3 = round(entry * 1.06, 6)

        message = f"""
🚀 Breakout Signal

Symbol: {symbol}
Entry: {entry}

TP1: {tp1} (2%)
TP2: {tp2} (4%)
TP3: {tp3} (6%)

Time: {datetime.now().strftime('%H:%M:%S')}
"""
        send_telegram(message)

# =========================
# MAIN LOOP
# =========================

def main():
    send_telegram("🚀 Bot Started")

    last_heartbeat = time.time()

    while True:
        print("New scan cycle")
        symbols = get_usdt_pairs()

        for symbol in symbols:
            try:
                check_signal(symbol)
            except:
                pass

        # Heartbeat every hour
        if time.time() - last_heartbeat > 3600:
            send_telegram("🟢 Bot Running - Still Scanning")
            last_heartbeat = time.time()

        time.sleep(300)  # كل 5 دقائق

if __name__ == "__main__":
    main()
