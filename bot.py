import os
import time
import requests
from datetime import datetime

# ==============================
# ENV VARIABLES
# ==============================

TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
TELEGRAM_CHAT_ID = os.getenv("7960335113")

print("Loaded TOKEN:", TELEGRAM_TOKEN is not None)
print("Loaded CHAT_ID:", TELEGRAM_CHAT_ID is not None)

# ==============================
# TELEGRAM SEND FUNCTION
# ==============================

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# GET 150 USDT PAIRS SAFE
# ==============================

def get_usdt_pairs():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print("Binance API error:", response.status_code)
            return []

        data = response.json()

        if "symbols" not in data:
            print("Unexpected Binance response")
            return []

        pairs = []
        for s in data["symbols"]:
            if s["quoteAsset"] == "USDT" and s["status"] == "TRADING":
                pairs.append(s["symbol"])

        return pairs[:150]

    except Exception as e:
        print("Error fetching pairs:", e)
        return []

# ==============================
# SIMPLE SCAN LOGIC
# ==============================

def scan_market():
    pairs = get_usdt_pairs()

    if not pairs:
        print("No pairs fetched")
        return

    print(f"Scanning {len(pairs)} pairs")

    for symbol in pairs:
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            r = requests.get(url, timeout=5)

            if r.status_code != 200:
                continue

            data = r.json()

            change = float(data["priceChangePercent"])

            # شرط بسيط غير صارم ولا خفيف
            if 2.5 < change < 6:
                price = data["lastPrice"]

                message = (
                    f"🚀 فرصة محتملة\n"
                    f"{symbol}\n"
                    f"السعر الحالي: {price}\n"
                    f"نسبة الارتفاع 24h: {round(change,2)}%\n"
                    f"فحص: {datetime.now().strftime('%H:%M')}"
                )

                send_telegram(message)

        except:
            continue

# ==============================
# MAIN LOOP
# ==============================

def main():
    send_telegram("✅ البوت اشتغل وبدأ الفحص")

    last_heartbeat = time.time()

    while True:
        print("New scan cycle")
        scan_market()

        # رسالة كل ساعة
        if time.time() - last_heartbeat >= 3600:
            send_telegram("💚 البوت شغال ويفحص السوق")
            last_heartbeat = time.time()

        time.sleep(300)  # كل 5 دقائق

if __name__ == "__main__":
    main()
