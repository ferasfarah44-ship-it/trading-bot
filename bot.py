import os
import time
import requests
import pandas as pd
import ta
from datetime import datetime, timedelta

# ====== CONFIG ======
ENABLE_PULLBACK = True
ENABLE_REVERSAL = True
ENABLE_MOMENTUM = True

COOLDOWN_MINUTES = 40
MIN_RR = 1.3

TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
CHAT_ID = os.getenv("7960335113")

sent_signals = {}

# ================= TELEGRAM =================
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=10)
        print("Signal sent")
    except Exception as e:
        print("Telegram error:", e)

# ================= REQUEST =================
def safe_request(url):
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# ================= ANALYZE =================
def analyze(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=120"
    klines = safe_request(url)
    if not klines:
        return

    df = pd.DataFrame(klines)
    df["close"] = df[4].astype(float)
    df["high"] = df[2].astype(float)
    df["low"] = df[3].astype(float)
    df["volume"] = df[5].astype(float)

    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["ma25"] = df["close"].rolling(25).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    now = datetime.now()
    if symbol in sent_signals:
        if now - sent_signals[symbol] < timedelta(minutes=COOLDOWN_MINUTES):
            return

    volume_avg = df["volume"].rolling(20).mean().iloc[-1]

    # ================= PULLBACK MODE =================
    if ENABLE_PULLBACK:
        rsi_cross = prev["rsi"] < 50 and last["rsi"] > 50
        volume_spike = last["volume"] > 2 * volume_avg
        breakout = last["close"] > df["high"][-7:-1].max()

        if rsi_cross and volume_spike and breakout:
            high_break = last["high"]
            pullback_zone = high_break * 0.985

            if last["close"] <= pullback_zone and last["rsi"] > 50:
                stop = df["low"][-7:-1].min()
                risk = last["close"] - stop
                if risk <= 0:
                    return

                target = last["close"] + (risk * 1.5)
                rr = (target - last["close"]) / risk

                if rr >= MIN_RR:
                    message = f"""
🟢 PULLBACK SIGNAL
{symbol}

Entry: {round(last['close'],4)}
Stop: {round(stop,4)}
Target: {round(target,4)}
RR: {round(rr,2)}
"""
                    send_telegram(message)
                    sent_signals[symbol] = now
                    return

    # ================= MOMENTUM MODE =================
    if ENABLE_MOMENTUM:
        body_percent = abs(last["close"] - prev["close"]) / prev["close"] * 100
        strong_volume = last["volume"] > 3 * volume_avg
        breakout10 = last["close"] > df["high"][-11:-1].max()

        if body_percent >= 4 and strong_volume and breakout10 and 55 < last["rsi"] < 80:
            stop = last["close"] * 0.975
            risk = last["close"] - stop
            target = last["close"] + (risk * 1.3)

            message = f"""
🔴 MOMENTUM SIGNAL
{symbol}

Entry: {round(last['close'],4)}
Stop: {round(stop,4)}
Target: {round(target,4)}
"""
            send_telegram(message)
            sent_signals[symbol] = now
            return

    # ================= REVERSAL MODE =================
    if ENABLE_REVERSAL:
        rsi_reversal = prev["rsi"] < 40 and last["rsi"] > 50
        ma_break = last["close"] > last["ma25"]
        volume_ok = last["volume"] > 1.5 * volume_avg

        if rsi_reversal and ma_break and volume_ok:
            stop = df["low"][-10:-1].min()
            risk = last["close"] - stop
            if risk <= 0:
                return

            target = last["close"] + (risk * 1.5)

            message = f"""
🟡 REVERSAL SIGNAL
{symbol}

Entry: {round(last['close'],4)}
Stop: {round(stop,4)}
Target: {round(target,4)}
"""
            send_telegram(message)
            sent_signals[symbol] = now
            return

# ================= MAIN LOOP =================
def main():
    print("New scan cycle")
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

    for symbol in symbols[:250]:
        analyze(symbol)

if __name__ == "__main__":
    while True:
        try:
            main()
            time.sleep(300)
        except Exception as e:
            print("Crash prevented:", e)
            time.sleep(10)
