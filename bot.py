import requests
import time
import statistics

BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

SENT_ALERTS = {}
LAST_HEARTBEAT = time.time()



# ================= TELEGRAM =================

def send_telegram(msg, symbol=None, is_alert=False):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        if symbol:
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📊 فتح على Binance",
                            "url": f"https://www.binance.com/en/trade/{symbol}"
                        }
                    ]
                ]
            }
        else:
            keyboard = None

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
        # ===== 5m =====
        r5 = requests.get(f"{BASE}/klines",
                          params={"symbol": sym, "interval": "5m", "limit": 100},
                          timeout=10)

        if r5.status_code != 200:
            return None

        k5 = r5.json()

        closes_5m = [float(x[4]) for x in k5]
        highs_5m = [float(x[2]) for x in k5]
        vols_5m = [float(x[5]) for x in k5]

        price_5m = closes_5m[-1]
        open_5m = float(k5[-1][1])
        vol_now = vols_5m[-1]
        vol_avg = statistics.mean(vols_5m[-20:-1])

        rsi_current = calculate_rsi(closes_5m)
        rsi_prev1 = calculate_rsi(closes_5m[:-1])
        rsi_prev2 = calculate_rsi(closes_5m[:-2])

        ema20 = calculate_ema(closes_5m, 20)
        ema50 = calculate_ema(closes_5m, 50)

        move_pct = (price_5m - open_5m) / open_5m

        signal_types = []

        # ===== FLOW =====
        if vol_now > vol_avg * 2.2 and move_pct > 0.008 and price_5m > ema20:
            signal_types.append("🔥 تدفق سيولة")

        # ===== SCALPING =====
        if (rsi_prev2 and rsi_prev1 and rsi_current and
            rsi_prev2 < 55 and
            rsi_prev1 > 55 and
            rsi_current > rsi_prev1 and
            vol_now > vol_avg * 1.5 and
            price_5m > ema20 and
            price_5m > max(highs_5m[-6:-1])):
            signal_types.append("⚡ سكالبينج")

        # ===== TREND BUILD =====
        if (ema20 > ema50 and
            price_5m > ema20 and
            rsi_current and 55 < rsi_current < 75 and
            vol_now > vol_avg * 1.4 and
            price_5m > max(highs_5m[-9:-1])):
            signal_types.append("🟢 Trend Build")

        # ===== SWING =====
        r1 = requests.get(f"{BASE}/klines",
                          params={"symbol": sym, "interval": "1h", "limit": 100},
                          timeout=10)

        if r1.status_code == 200:
            k1 = r1.json()
            closes_1h = [float(x[4]) for x in k1]
            highs_1h = [float(x[2]) for x in k1]
            vols_1h = [float(x[5]) for x in k1]

            price_1h = closes_1h[-1]
            vol_1h = vols_1h[-1]
            vol_avg_1h = statistics.mean(vols_1h[-20:-1])

            rsi_1h = calculate_rsi(closes_1h)
            ema50_1h = calculate_ema(closes_1h, 50)

            if (price_1h > ema50_1h and
                rsi_1h and rsi_1h > 52 and
                price_1h > max(highs_1h[-13:-1]) and
                vol_1h > vol_avg_1h * 1.3):
                signal_types.append("📈 سوينج")

        if not signal_types:
            return None

        entry = price_5m
        tp1 = entry * 1.02
        tp2 = entry * 1.04
        tp3 = entry * 1.07
        sl = entry * 0.985

        return (
            f"🚀 إشارة متعددة\n\n"
            f"🪙 {sym}\n"
            f"📊 الأنواع:\n- " + "\n- ".join(signal_types) + "\n\n"
            f"💰 دخول: {entry:.6f}\n\n"
            f"🎯 TP1: {tp1:.6f}\n"
            f"🎯 TP2: {tp2:.6f}\n"
            f"🎯 TP3: {tp3:.6f}\n"
            f"🛑 SL: {sl:.6f}"
        )

    except Exception as e:
        print("Signal ERROR:", e)
        return None


# ================= LOOP =================

def run_scanner():
    global LAST_HEARTBEAT

    send_telegram("🛰️ تم تشغيل الرادار المتوازن")

    while True:

        if time.time() - LAST_HEARTBEAT >= 3600:
            send_telegram("✅ فحص مستمر — لا توجد فرص حالياً.")
            LAST_HEARTBEAT = time.time()

        try:
            r = requests.get(f"{BASE}/exchangeInfo", timeout=10)

            if r.status_code != 200:
                time.sleep(10)
                continue

            data = r.json()

            if "symbols" not in data:
                time.sleep(10)
                continue

            symbols = [
                s["symbol"]
                for s in data["symbols"]
                if s.get("quoteAsset") == "USDT"
                and s.get("status") == "TRADING"
            ]

            for symbol in symbols:
                signal = get_signal(symbol)

                if signal:
                    now = time.time()
                    if symbol not in SENT_ALERTS or (now - SENT_ALERTS[symbol] > 7200):
                        send_telegram(signal, symbol=symbol, is_alert=True)
                        SENT_ALERTS[symbol] = now

                time.sleep(0.07)

        except Exception as e:
            print("Scanner ERROR:", e)
            time.sleep(10)

        time.sleep(5)


if __name__ == "__main__":
    run_scanner()
