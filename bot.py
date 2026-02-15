import requests
import time
import statistics
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================== SETTINGS ==================

BOT_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"
BASE = "https://api.binance.com/api/v3"

SENT_ALERTS = {}
LAST_HEARTBEAT = time.time()

# ================== WEB SERVER (ANTI SLEEP) ==================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Running")

def run_web():
    port = 8080
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ================== TELEGRAM ==================

def send_telegram(msg, symbol=None):
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
            "parse_mode": "HTML"
        }

        if keyboard:
            payload["reply_markup"] = keyboard

        r = requests.post(url, json=payload, timeout=10)
        print("Telegram:", r.text)

    except Exception as e:
        print("Telegram ERROR:", e)

# ================== INDICATORS ==================

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

# ================== SIGNAL LOGIC ==================

def get_signal(sym):
    try:
        r = requests.get(f"{BASE}/klines",
                         params={"symbol": sym, "interval": "5m", "limit": 80},
                         timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        closes = [float(x[4]) for x in data]
        highs = [float(x[2]) for x in data]
        vols = [float(x[5]) for x in data]

        price = closes[-1]
        open_price = float(data[-1][1])
        move_pct = (price - open_price) / open_price

        vol_now = vols[-1]
        vol_avg = statistics.mean(vols[-25:-1])

        rsi = calculate_rsi(closes)
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50)

        if not rsi:
            return None

        # ================== تقوية الصيد ==================

        # انفجار قوي
        if vol_now > vol_avg * 2 and move_pct > 0.01:
            signal_type = "🚀 انفجار سيولة"

        # سكالبينج اختراق
        elif (price > max(highs[-6:-1]) and
              vol_now > vol_avg * 1.5 and
              rsi > 50 and
              price > ema20):
            signal_type = "⚡ سكالبينج اختراق"

        # ترند بناء
        elif (ema20 > ema50 and
              rsi > 52 and
              vol_now > vol_avg * 1.3 and
              price > ema20):
            signal_type = "📈 بناء ترند"

        else:
            return None

        tp1 = price * 1.02
        tp2 = price * 1.04
        tp3 = price * 1.07
        sl = price * 0.985

        msg = (
            f"<b>{signal_type}</b>\n\n"
            f"🪙 <b>{sym}</b>\n"
            f"💰 دخول: <b>{price:.6f}</b>\n"
            f"📊 RSI: {rsi:.1f}\n"
            f"🔥 قوة سيولة: {vol_now/vol_avg:.1f}x\n\n"
            f"🎯 TP1: {tp1:.6f}\n"
            f"🎯 TP2: {tp2:.6f}\n"
            f"🎯 TP3: {tp3:.6f}\n"
            f"🛑 SL: {sl:.6f}"
        )

        return msg

    except Exception as e:
        print("Signal ERROR:", sym, e)
        return None

# ================== SCANNER ==================

def run_scanner():
    send_telegram("🛰️ تم تشغيل رادار الصيد المتطور")

    while True:
        try:
            print("Scanning cycle running...")

            tick = requests.get(f"{BASE}/ticker/24hr", timeout=10).json()
            usdt_pairs = [x for x in tick if x["symbol"].endswith("USDT")]
            usdt_pairs.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)

            top_symbols = [x["symbol"] for x in usdt_pairs[:120]]

            print("Scanning top", len(top_symbols), "symbols...")

            for symbol in top_symbols:
                signal = get_signal(symbol)

                if signal:
                    now = time.time()
                    if symbol not in SENT_ALERTS or now - SENT_ALERTS[symbol] > 3600:
                        send_telegram(signal, symbol)
                        SENT_ALERTS[symbol] = now

                time.sleep(0.07)

            # heartbeat
            if time.time() - LAST_HEARTBEAT > 60:
                print("Heartbeat OK")
            
            time.sleep(5)

        except Exception as e:
            print("Scanner ERROR:", e)
            time.sleep(10)

# ================== START ==================

if __name__ == "__main__":
    print("=== BOT STARTED SUCCESSFULLY ===")
    run_scanner()
