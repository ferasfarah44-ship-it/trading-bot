import requests
import time
import os
from datetime import datetime
import pandas as pd

# ===============================
# ENV
# ===============================
TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
TELEGRAM_CHAT_ID = os.getenv("7960335113")

SCAN_INTERVAL = 300        # 5 minutes
HEARTBEAT_INTERVAL = 3600  # 1 hour
MAX_COINS = 150

last_heartbeat = time.time()

# ===============================
# TELEGRAM
# ===============================
def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ===============================
# GET USDT PAIRS
# ===============================
def get_usdt_pairs():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    data = requests.get(url).json()
    symbols = []
    for s in data["symbols"]:
        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING":
            symbols.append(s["symbol"])
    return symbols[:MAX_COINS]

# ===============================
# GET KLINES
# ===============================
def get_klines(symbol, interval="5m", limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    data = requests.get(url, params=params).json()
    df = pd.DataFrame(data)
    df = df.iloc[:, :6]
    df.columns = ["time","open","high","low","close","volume"]
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df["high"] = df["high"].astype(float)
    return df

# ===============================
# RSI
# ===============================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ===============================
# SIGNAL CHECK
# ===============================
def check_signal(symbol):
    df = get_klines(symbol)
    
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["rsi"] = calculate_rsi(df["close"])
    df["vol_avg"] = df["volume"].rolling(20).mean()
    
    last = df.iloc[-1]
    prev_high = df["high"].iloc[-21:-1].max()
    
    cond1 = last["close"] > last["ema20"]
    cond2 = last["ema20"] > last["ema50"]
    cond3 = 52 < last["rsi"] < 68
    cond4 = last["volume"] > last["vol_avg"] * 1.3
    cond5 = last["close"] > prev_high
    
    if cond1 and cond2 and cond3 and cond4 and cond5:
        entry = last["close"]
        target1 = entry * 1.02
        target2 = entry * 1.04
        stop = entry * 0.98
        
        message = (
            f"🚀 SIGNAL: {symbol}\n"
            f"Entry: {entry:.6f}\n"
            f"TP1: {target1:.6f} (+2%)\n"
            f"TP2: {target2:.6f} (+4%)\n"
            f"Stop: {stop:.6f} (-2%)"
        )
        send_telegram(message)

# ===============================
# MAIN LOOP
# ===============================
def main():
    global last_heartbeat
    
    send_telegram("🚀 Trading Bot Started")
    
    while True:
        try:
            print("New scan cycle:", datetime.now())
            symbols = get_usdt_pairs()
            
            for symbol in symbols:
                try:
                    check_signal(symbol)
                except:
                    continue
            
            # heartbeat
            if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                send_telegram("✅ Bot running and scanning every 5 minutes")
                last_heartbeat = time.time()
            
        except Exception as e:
            print("Main loop error:", e)
        
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
