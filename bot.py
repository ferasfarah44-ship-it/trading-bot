import requests
import time
import statistics

# ========= الإعدادات =========
BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

SENT_ALERTS = {}
LAST_HEARTBEAT = time.time()

# ========= TELEGRAM =========

def send_telegram(msg, symbol=None, is_alert=False):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "disable_notification": False if is_alert else True
        }

        if symbol:
            payload["reply_markup"] = {
                "inline_keyboard": [[
                    {
                        "text": "📊 فتح على Binance",
                        "url": f"https://www.binance.com/en/trade/{symbol}"
                    }
                ]]
            }

        r = requests.post(url, json=payload, timeout=10)
        print("Telegram:", r.text)

    except Exception as e:
        print("Telegram ERROR:", e)

# ========= INDICATORS =========

def calculate_rsi(prices, period=14):
    if len(prices) < period + 2:
        return None

    gains = []
    losses = []

    for i in range(1, period + 1):
        delta = prices[-i] - prices[-i-1]
        if delta >= 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

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

# ========= SIGNAL =========

def get_signal(sym):
    try:
        r = requests.get(f"{BASE}/klines",
                         params={"symbol": sym, "interval": "5m", "limit": 100},
                         timeout=10)

        if r.status_code != 200:
            return None

        k = r.json()

        closes = [float(x[4]) for x in k]
        highs = [float(x[2]) for x in k]
        vols = [float(x[5]) for x in k]

        price = closes[-1]
        open_price = float(k[-1][1])
        vol_now = vols[-1]
        vol_avg = statistics.mean(vols[-20:-1])

        rsi = calculate_rsi(closes)
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50)

        move_pct = (price - open_price) / open_price

        signal_type = None

        # 🚀 انفجار
        if vol_now > vol_avg * 2.5 and move_pct > 0.015:
            signal_type = "🚀 انفجار سعري"

        # 🔥 تدفق سيولة
        elif vol_now > vol_avg * 1.8 and price > ema20:
            signal_type = "🔥 تدفق سيولة"

        # ⚡ سكالبينج
        elif rsi and rsi > 55 and vol_now > vol_avg * 1.5 and price > max(highs[-5:-1]):
            signal_type = "⚡ سكالبينج"

        # 🟢 اتجاه صاعد
        elif ema20 > ema50 and rsi and rsi > 52:
            signal_type = "🟢 اتجاه صاعد"

        if not signal_type:
            return None

        entry = price
        tp1 = entry * 1.02
        tp2 = entry * 1.04
        tp3 = entry * 1.06
        sl = entry * 0.985

        return f"""
🚨 إشارة قوية مكتشفة

🪙 العملة: {sym}
📌 النوع: {signal_type}

💰 دخول: {entry:.6f}
📈 RSI: {rsi:.2f if rsi else 0}
🔥 قوة الفوليوم: {vol_now/vol_avg:.1f}x

🎯 الهدف 1: {tp1:.6f}
🎯 الهدف 2: {tp2:.6f}
🎯 الهدف 3: {tp3:.6f}
🛑 وقف: {sl:.6f}
"""

    except Exception as e:
        print("Signal ERROR:", e)
        return None

# ========= LOOP =========

def run_scanner():
    global LAST_HEARTBEAT

    print("=== BOT STARTED SUCCESSFULLY ===")
    send_telegram("🛰️ الرادار بدأ العمل...")

    while True:

        if time.time() - LAST_HEARTBEAT >= 3600:
            send_telegram("✅ الرادار يعمل بشكل طبيعي.")
            LAST_HEARTBEAT = time.time()

        try:
            r = requests.get(f"{BASE}/exchangeInfo", timeout=10)
            if r.status_code != 200:
                time.sleep(10)
                continue

            symbols = [
                s["symbol"]
                for s in r.json()["symbols"]
                if s.get("quoteAsset") == "USDT"
                and s.get("status") == "TRADING"
            ]

            # مسح أول 120 عملة فقط
            symbols = symbols[:120]

            print(f"Scanning top {len(symbols)} symbols...")

            for symbol in symbols:
                signal = get_signal(symbol)

                if signal:
                    now = time.time()
                    if symbol not in SENT_ALERTS or now - SENT_ALERTS[symbol] > 7200:
                        send_telegram(signal, symbol=symbol, is_alert=True)
                        SENT_ALERTS[symbol] = now

                time.sleep(0.15)

        except Exception as e:
            print("Scanner ERROR:", e)
            time.sleep(10)

        time.sleep(5)


if __name__ == "__main__":
    run_scanner()
