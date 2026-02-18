import os
import time
import requests
import pandas as pd
import ta
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
CHAT_ID = os.getenv("7960335113")

COOLDOWN_MINUTES = 45
MIN_RR = 1.5

sent_signals = {}
breakout_memory = {}

# ========= TELEGRAM =========
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=10)
        print("Signal sent to Telegram")
    except Exception as e:
        print("Telegram error:", e)

# ========= SAFE REQUEST =========
def safe_request(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print("Request failed:", r.status_code)
            return None
        data = r.json()
        if isinstance(data, dict) and "code" in data:
            print("Binance error:", data)
            return None
        return data
    except Exception as e:
        print("Request exception:", e)
        return None

# ========= GET KLINES =========
def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=120"
    return safe_request(url)

# ========= ANALYZE =========
def analyze(symbol):
    klines = get_klines(symbol)
    if not klines:
        return

    df = pd.DataFrame(klines)

    df["close"] = df[4].astype(float)
    df["high"] = df[2].astype(float)
    df["low"] = df[3].astype(float)
    df["volume"] = df[5].astype(float)
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # ===== PHASE 1: DETECT MOMENTUM =====
    rsi_cross = prev["rsi"] < 50 and last["rsi"] > 50
    volume_spike = last["volume"] > 2 * df["volume"].rolling(20).mean().iloc[-1]
    micro_break = last["close"] > df["high"][-7:-1].max()

    if rsi_cross and volume_spike and micro_break:
        breakout_memory[symbol] = {
            "high_break": last["high"],
            "volume_break": last["volume"],
            "break_low": df["low"][-7:-1].min(),
            "time": datetime.now()
        }
        print(f"{symbol} breakout detected")

    # ===== PHASE 2: WAIT PULLBACK =====
    if symbol in breakout_memory:
        data = breakout_memory[symbol]
        high_break = data["high_break"]
        volume_break = data["volume_break"]
        structure_low = data["break_low"]

        pullback_low = high_break * 0.98
        pullback_high = high_break * 0.99

        in_pullback = pullback_low <= last["close"] <= pullback_high
        rsi_ok = last["rsi"] > 50
        low_volume_pullback = last["volume"] < volume_break

        if in_pullback and rsi_ok and low_volume_pullback:

            now = datetime.now()
            if symbol in sent_signals:
                if now - sent_signals[symbol] < timedelta(minutes=COOLDOWN_MINUTES):
                    return

            entry = last["close"]
            stop = structure_low

            if stop >= entry:
                return

            risk = entry - stop
            if risk <= 0:
                return

            # ===== TARGET 1: NEAREST RESISTANCE =====
            recent_highs = df["high"][-40:]
            resistance = recent_highs[recent_highs > entry].min()

            if pd.isna(resistance):
                return

            target1 = resistance

            # ===== TARGET 2: MEASURED MOVE =====
            measured_move = high_break - structure_low
            target2 = entry + measured_move

            rr = (target1 - entry) / risk

            if rr < MIN_RR:
                print(f"{symbol} rejected due to low RR")
                return

            message = f"""
🚀 {symbol}

Entry: {round(entry,4)}
Stop: {round(stop,4)}

Target1 (Resistance): {round(target1,4)}
Target2 (Measured Move): {round(target2,4)}

RR: {round(rr,2)}
"""

            send_telegram(message)
            sent_signals[symbol] = now
            del breakout_memory[symbol]

# ========= MAIN LOOP =========
def main():
    print("---- New Scan Cycle ----")
    exchange = safe_request("https://api.binance.com/api/v3/exchangeInfo")
    if not exchange:
        print("Exchange fetch failed")
        return

    symbols = [
        s["symbol"] for s in exchange["symbols"]
        if s["quoteAsset"] == "USDT"
        and s["status"] == "TRADING"
        and not s["symbol"].endswith("UPUSDT")
        and not s["symbol"].endswith("DOWNUSDT")
    ]

    print(f"Scanning {len(symbols)} symbols...")

    for symbol in symbols:
        analyze(symbol)

    print("Cycle finished.\n")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(300)
