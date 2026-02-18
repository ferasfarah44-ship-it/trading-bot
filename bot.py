import os
import time
import requests
import pandas as pd
import ta
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
CHAT_ID = os.getenv("7960335113")

COOLDOWN_MINUTES = 45
MIN_RR = 1.5  # أقل نسبة ربح/مخاطرة مقبولة

sent_signals = {}
breakout_memory = {}

# ========= TELEGRAM =========
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=10)
    except:
        pass

# ========= SAFE REQUEST =========
def safe_request(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, dict) and "code" in data:
            return None
        return data
    except:
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

    # ======================
    # PHASE 1: DETECT MOMENTUM START
    # ======================
    rsi_cross = prev["rsi"] < 50 and last["rsi"] > 50
    volume_spike = last["volume"] > 2 * df["volume"].rolling(20).mean().iloc[-1]
    micro_break = last["close"] > df["high"][-7:-1].max()

    if rsi_cross and volume_spike and micro_break:
        breakout_memory[symbol] = {
            "high_break": last["high"],
            "volume_break": last["volume"],
            "break_low": df["low"][-7:-1].min(),  # قاع الهيكل القصير
            "time": datetime.now()
        }

    # ======================
    # PHASE 2: PULLBACK ENTRY
    # ======================
    if symbol in breakout_memory:
        data = breakout_memory[symbol]
        high_break = data["high_break"]
        volume_break = data["volume_break"]
        structure_low = data["break_low"]

        # منطقة الرجوع 1% - 2%
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

            # ========= STOP LOSS من الهيكل =========
            stop = structure_low
            if stop >= entry:
                return

            risk = entry - stop
            if risk <= 0:
                return

            # ========= TARGET 1 = أقرب مقاومة =========
            recent_highs = df["high"][-40:]
            resistance = recent_highs[recent_highs > entry].min()

            if pd.isna(resistance):
                return

            target1 = resistance

            # ========= TARGET 2 = Measured Move =========
            measured_move = high_break - structure_low
            target2 = entry + measured_move

            # ========= فلتر RR =========
            rr = (target1 - entry) / risk

            if rr < MIN_RR:
                return

            message = f"""
🚀 {symbol}

Entry: {round(entry,4)}
Stop (Structure Low): {round(stop,4)}

Target 1 (Resistance): {round(target1,4)}
Target 2 (Measured Move): {round(target2,4)}

Risk/Reward: {round(rr,2)}
Strategy: Momentum + Pullback + Structure
"""

            send_telegram(message)
            sent_signals[symbol] = now
            del breakout_memory[symbol]

# ========= MAIN LOOP =========
def main():
    exchange = safe_request("https://api.binance.com/api/v3/exchangeInfo")
    if not exchange:
        return

    symbols = [
        s["symbol"] for s in exchange["symbols"]
        if s["quoteAsset"] == "USDT"
        and s["status"] == "TRADING"
        and not s["symbol"].endswith("UPUSDT")
        and not s["symbol"].endswith("DOWNUSDT")
    ]

    for symbol in symbols:
        analyze(symbol)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(300)
