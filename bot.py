import os
import time
import requests
from datetime import datetime

# =========================
# ENV DEBUG (مهم جداً)
# =========================

print("===== ENV DEBUG START =====")
print("ENV KEYS:", list(os.environ.keys()))
print("TOKEN VALUE:", os.environ.get("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"))
print("CHAT_ID VALUE:", os.environ.get("7960335113"))
print("===== ENV DEBUG END =====")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# =========================
# TELEGRAM FUNCTION
# =========================

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
        print("Telegram sent")
    except Exception as e:
        print("Telegram error:", e)

# =========================
# GET TOP 150 USDT PAIRS
# =========================

def get_usdt_pairs():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        data = requests.get(url, timeout=10).json()

        usdt_pairs = [
            s["symbol"] for s in data
            if s["symbol"].endswith("USDT")
        ]

        # ترتيب حسب حجم التداول
        sorted_pairs = sorted(
            data,
            key=lambda x: float(x["quoteVolume"]),
            reverse=True
        )

        final = [
            s["symbol"] for s in sorted_pairs
            if s["symbol"].endswith("USDT")
        ]

        return final[:150]

    except Exception as e:
        print("Error fetching pairs:", e)
        return []

# =========================
# MAIN LOOP
# =========================

def main():
    send_telegram("🚀 Bot Started Successfully")

    last_heartbeat = time.time()

    while True:
        print("New scan cycle", datetime.now())
        
        pairs = get_usdt_pairs()
        print("Scanning", len(pairs), "pairs")

        # === مكان منطق الاشارة تبعك ===
        # حالياً فقط فحص

        # رسالة كل ساعة
        if time.time() - last_heartbeat > 3600:
            send_telegram("✅ Bot still running and scanning")
            last_heartbeat = time.time()

        time.sleep(300)  # كل 5 دقائق

# =========================

if __name__ == "__main__":
    main()
