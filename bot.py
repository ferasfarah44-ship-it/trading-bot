import requests
import time
import statistics

BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

SENT_ALERTS = {}
LAST_HEARTBEAT = time.time()
BOT_STATUS = "تشغيل تلقائي 🟢"


# ================= TELEGRAM =================

def send_telegram(msg, symbol=None, is_alert=False):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        # أزرار التحكم الأساسية
        main_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🔄 فحص الآن", "callback_data": "scan"},
                    {"text": "🛑 إيقاف", "callback_data": "stop"},
                ],
                [
                    {"text": "🟢 تشغيل تلقائي", "callback_data": "start"}
                ]
            ]
        }

        # أزرار العملة عند وجود فرصة
        if symbol:
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📊 فتح على Binance",
                            "url": f"https://www.binance.com/en/trade/{symbol}"
                        }
                    ],
                    [
                        {
                            "text": "🕌 الحكم الشرعي",
                            "url": f"https://cryptoislam.com/search?q={symbol.replace('USDT','')}"
                        }
                    ]
                ]
            }
        else:
            keyboard = main_keyboard

        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "reply_markup": keyboard,
            "disable_notification": False if is_alert else True
        }

        r = requests.post(url, json=payload, timeout=10)

        print("Telegram:", r.status_code, r.text)

    except Exception as e:
        print("Telegram ERROR:", e)


# ================= INDICATORS =================

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50

    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_ema(prices, period=20):
    if len(prices) < period:
        return prices[-1]

    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period

    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


# ================= SIGNAL =================

def get_signal(sym):
    try:
        params = {"symbol": sym, "interval": "5m", "limit": 50}
        r = requests.get(f"{BASE}/klines", params=params, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        closes = [float(k[4]) for k in data]
        vols = [float(k[5]) for k in data]

        current_price = closes[-1]
        open_price = float(data[-1][1])
        vol_now = vols[-1]
        vol_avg = statistics.mean(vols[-20:-1])

        rsi_val = calculate_rsi(closes)
        ema_val = calculate_ema(closes)

        if (
            vol_now > vol_avg * 1.8
            and current_price > ema_val
            and 55 < rsi_val < 70
        ):
            entry = current_price
            tp1 = entry * 1.015
            tp2 = entry * 1.03
            sl = entry * 0.988

            return (
                f"🚀 فرصة تداول\n\n"
                f"العملة: {sym}\n"
                f"الدخول: {entry:.6f}\n"
                f"RSI: {rsi_val:.2f}\n\n"
                f"TP1: {tp1:.6f}\n"
                f"TP2: {tp2:.6f}\n"
                f"SL: {sl:.6f}"
            )

        return None

    except Exception as e:
        print("Signal ERROR:", e)
        return None


# ================= LOOP =================

def run_scanner():
    global LAST_HEARTBEAT

    print("Bot Started")
    send_telegram("🛰️ تم بدء تشغيل الرادار")

    while True:

        # رسالة الاطمئنان كل ساعة
        if time.time() - LAST_HEARTBEAT >= 3600:
            send_telegram("✅ تم الفحص — لا توجد فرص حالياً.")
            LAST_HEARTBEAT = time.time()

        try:
            r = requests.get(f"{BASE}/exchangeInfo", timeout=10)
            data = r.json()

            symbols = [
                s["symbol"]
                for s in data["symbols"]
                if s["quoteAsset"] == "USDT"
                and s["status"] == "TRADING"
            ]

            for symbol in symbols:
                signal = get_signal(symbol)

                if signal:
                    now = time.time()

                    if (
                        symbol not in SENT_ALERTS
                        or (now - SENT_ALERTS[symbol] > 7200)
                    ):
                        send_telegram(signal, symbol=symbol, is_alert=True)
                        SENT_ALERTS[symbol] = now

                time.sleep(0.05)

        except Exception as e:
            print("Scanner ERROR:", e)
            time.sleep(10)

        time.sleep(5)


if __name__ == "__main__":
    run_scanner()
