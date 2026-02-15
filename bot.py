import requests
import time
import statistics
import os

# ================== CONFIG ==================

BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

SENT_ALERTS = {}
LAST_HEARTBEAT = time.time()

# ================= TELEGRAM =================

def send_telegram(msg, symbol=None, is_alert=False):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        keyboard = None
        if symbol:
            keyboard = {
                "inline_keyboard": [[
                    {"text": "📊 فتح على Binance",
                     "url": f"https://www.binance.com/en/trade/{symbol}"}
                ]]
            }

        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "reply_markup": keyboard,
            "disable_notification": False if is_alert else True
        }

        requests.post(url, json=payload, timeout=10)

    except Exception as e:
        print("Telegram ERROR:", e)

# ================= INDICATORS =================

def calculate_rsi(prices, period=14):
    if len(prices) < period + 2:
        return None

    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(prices, period):
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
        r5 = requests.get(
            f"{BASE}/klines",
            params={"symbol": sym, "interval": "5m", "limit": 100},
            timeout=10
        )

        if r5.status_code != 200:
            return None

        k5 = r5.json()

        closes = [float(x[4]) for x in k5]
        highs = [float(x[2]) for x in k5]
        vols = [float(x[5]) for x in k5]

        price = closes[-1]
        open_price = float(k5[-1][1])

        vol_now = vols[-1]
        vol_avg = statistics.mean(vols[-20:-1])

        rsi_current = calculate_rsi(closes)
        rsi_prev1 = calculate_rsi(closes[:-1])
        rsi_prev2 = calculate_rsi(closes[:-2])

        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50)

        move_pct = (price - open_price) / open_price

        signal_types = []

        # 🚀 Parabolic
        if vol_now > vol_avg * 3.2 and move_pct > 0.018:
            signal_types.append("🚀 انفجار عمودي")

        # 🔥 Flow
        if vol_now > vol_avg * 2.2 and move_pct > 0.008 and price > ema20:
            signal_types.append("🔥 تدفق سيولة")

        # ⚡ Scalping
        if (rsi_prev2 and rsi_prev1 and rsi_current and
            rsi_prev2 < 55 and rsi_prev1 > 55 and
            vol_now > vol_avg * 1.5 and
            price > max(highs[-6:-1])):
            signal_types.append("⚡ سكالبينج")

        # 🟢 Trend Build
        if (ema20 > ema50 and
            rsi_current and 55 < rsi_current < 75 and
            vol_now > vol_avg * 1.4 and
            price > max(highs[-9:-1])):
            signal_types.append("🟢 Trend Build")

        if not signal_types:
            return None

        entry = price
        tp1 = entry * 1.02
        tp2 = entry * 1.04
        tp3 = entry * 1.07
        sl = entry * 0.985

        return (
            f"🚀 إشارة متعددة\n\n"
            f"🪙 {sym}\n"
            f"📊 الأنواع:\n- " + "\n- ".join(signal_types) + "\n\n"
            f"💰 دخول: {entry:.6f}\n"
            f"RSI: {rsi_current:.2f}\n"
            f"القوة: {vol_now/vol_avg:.1f}x\n\n"
            f"🎯 TP1: {tp1:.6f}\n"
            f"🎯 TP2: {tp2:.6f}\n"
            f"🎯 TP3: {tp3:.6f}\n"
            f"🛑 SL: {sl:.6f}"
        )

    except Exception as e:
        print("Signal ERROR:", sym, e)
        return None

# ================= LOOP =================

def run_scanner():
    global LAST_HEARTBEAT

    print("=== BOT STARTED SUCCESSFULLY ===")
    send_telegram("🛰️ تم تشغيل الرادار بنجاح")

    while True:
        print("Scanning cycle running...")

        if time.time() - LAST_HEARTBEAT >= 3600:
            send_telegram("✅ فحص مستمر — الرادار يعمل.")
            LAST_HEARTBEAT = time.time()

        try:
            r = requests.get(f"{BASE}/exchangeInfo", timeout=10)

            if r.status_code != 200:
                print("ExchangeInfo ERROR")
                time.sleep(10)
                continue

            symbols = [
                s["symbol"] for s in r.json()["symbols"]
                if s.get("quoteAsset") == "USDT"
                and s.get("status") == "TRADING"
            ]

            print("Total symbols:", len(symbols))

            for symbol in symbols:
                signal = get_signal(symbol)

                if signal:
                    now = time.time()
                    if symbol not in SENT_ALERTS or now - SENT_ALERTS[symbol] > 7200:
                        send_telegram(signal, symbol=symbol, is_alert=True)
                        SENT_ALERTS[symbol] = now
                        print("ALERT SENT:", symbol)

                time.sleep(0.08)

        except Exception as e:
            print("Scanner ERROR:", e)
            time.sleep(10)

        time.sleep(5)

# ================= START =================

if __name__ == "__main__":
    run_scanner()
