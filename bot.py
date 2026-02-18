import requests
import time
import os
import pandas as pd

# ==============================
# ====== SETTINGS =============
# ==============================

ENABLE_PULLBACK = True
ENABLE_REVERSAL = True
ENABLE_MOMENTUM = True

SCAN_INTERVAL = 15
HEARTBEAT_INTERVAL = 300

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"

TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
TELEGRAM_CHAT_ID = os.getenv("7960335113")

sent_signals = set()
last_heartbeat = time.time()


# ==============================
# ===== TELEGRAM ==============
# ==============================

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram ENV missing")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


# ==============================
# ===== INDICATORS ============
# ==============================

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ==============================
# ===== DATA FETCH ============
# ==============================

def get_symbols():
    try:
        data = requests.get(BINANCE_TICKER, timeout=10).json()
        symbols = []
        for s in data:
            if (
                s["symbol"].endswith("USDT")
                and float(s["quoteVolume"]) > 5000000
                and "UP" not in s["symbol"]
                and "DOWN" not in s["symbol"]
            ):
                symbols.append(s["symbol"])
        return symbols[:200]
    except:
        return []


def get_klines(symbol):
    try:
        params = {
            "symbol": symbol,
            "interval": "5m",
            "limit": 50
        }
        data = requests.get(BINANCE_KLINES, params=params, timeout=10).json()

        df = pd.DataFrame(data)
        df = df.iloc[:, 0:6]
        df.columns = ["time", "open", "high", "low", "close", "volume"]

        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["volume"] = df["volume"].astype(float)

        return df
    except:
        return None


# ==============================
# ===== MODES =================
# ==============================

def check_pullback(df):
    rsi = calculate_rsi(df["close"]).iloc[-1]
    volume_spike = df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1] * 2
    breakout = df["close"].iloc[-1] > df["high"].iloc[-6:-1].max()
    return rsi > 50 and volume_spike and breakout


def check_momentum(df):
    body = abs(df["close"].iloc[-1] - df["close"].iloc[-2])
    body_percent = (body / df["close"].iloc[-2]) * 100
    volume_spike = df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1] * 3
    rsi = calculate_rsi(df["close"]).iloc[-1]
    return body_percent > 4 and volume_spike and 55 < rsi < 80


def check_reversal(df):
    rsi_series = calculate_rsi(df["close"])
    rsi_now = rsi_series.iloc[-1]
    rsi_prev = rsi_series.iloc[-3]
    ma25 = df["close"].rolling(25).mean().iloc[-1]
    volume_spike = df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1] * 1.5
    return rsi_prev < 40 and rsi_now > 50 and df["close"].iloc[-1] > ma25 and volume_spike


# ==============================
# ===== TARGET LOGIC ==========
# ==============================

def calculate_targets(df):
    entry = df["close"].iloc[-1]
    resistance = df["high"].iloc[-10:-1].max()
    stop = df["low"].iloc[-5:-1].min()

    tp_percent = ((resistance - entry) / entry) * 100
    sl_percent = ((entry - stop) / entry) * 100

    return entry, resistance, stop, tp_percent, sl_percent


def send_signal(symbol, mode, entry, tp, sl, tp_percent):
    message = (
        f"🚨 <b>{mode}</b>\n"
        f"💎 {symbol}\n"
        f"💰 Entry: {entry:.5f}\n"
        f"🎯 Target: {tp:.5f} ({tp_percent:.2f}%)\n"
        f"🛑 Stop: {sl:.5f}"
    )
    send_telegram(message)


# ==============================
# ===== MAIN SCAN =============
# ==============================

def scan_market():
    symbols = get_symbols()
    for symbol in symbols:
        df = get_klines(symbol)
        if df is None:
            continue

        entry, tp, sl, tp_percent, sl_percent = calculate_targets(df)

        if ENABLE_PULLBACK and check_pullback(df):
            signal_id = f"{symbol}_pullback"
            if signal_id not in sent_signals:
                send_signal(symbol, "PULLBACK", entry, tp, sl, tp_percent)
                sent_signals.add(signal_id)

        if ENABLE_MOMENTUM and check_momentum(df):
            signal_id = f"{symbol}_momentum"
            if signal_id not in sent_signals:
                send_signal(symbol, "MOMENTUM", entry, tp, sl, tp_percent)
                sent_signals.add(signal_id)

        if ENABLE_REVERSAL and check_reversal(df):
            signal_id = f"{symbol}_reversal"
            if signal_id not in sent_signals:
                send_signal(symbol, "REVERSAL", entry, tp, sl, tp_percent)
                sent_signals.add(signal_id)


# ==============================
# ===== RUN ====================
# ==============================

if __name__ == "__main__":
    send_telegram(
        "🚀 Bot Started Successfully\n"
        f"Pullback: {ENABLE_PULLBACK}\n"
        f"Reversal: {ENABLE_REVERSAL}\n"
        f"Momentum: {ENABLE_MOMENTUM}"
    )

    while True:
        try:
            scan_market()

            now = time.time()
            if now - last_heartbeat > HEARTBEAT_INTERVAL:
                send_telegram("✅ البوت يعمل ويفحص السوق...")
                last_heartbeat = now

            time.sleep(SCAN_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(5)
