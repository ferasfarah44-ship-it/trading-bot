import requests
import pandas as pd
import time
import ta

# Telegram
TELEGRAM_TOKEN = "PUT_YOUR_BOT_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

# العملات
coins = [
"BTCUSDT","ETHUSDT","SOLUSDT","NEARUSDT","OPUSDT","LINKUSDT","ARBUSDT",
"BNBUSDT","AVAXUSDT","MATICUSDT","ATOMUSDT","INJUSDT","FETUSDT","RNDRUSDT"
]

# ارسال رسالة
def send_telegram(msg):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    requests.post(url,data=data)

# جلب بيانات Binance
def get_data(symbol):

    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=200"

    data = requests.get(url).json()

    df = pd.DataFrame(data)

    df = df.iloc[:,0:6]
    df.columns = ["time","open","high","low","close","volume"]

    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df

# التحليل
def analyze(symbol):

    df = get_data(symbol)

    df["ema20"] = ta.trend.ema_indicator(df["close"],20)
    df["ema50"] = ta.trend.ema_indicator(df["close"],50)

    df["rsi"] = ta.momentum.rsi(df["close"],14)

    macd = ta.trend.MACD(df["close"])

    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    price = df["close"].iloc[-1]

    ema20 = df["ema20"].iloc[-1]
    ema50 = df["ema50"].iloc[-1]

    rsi = df["rsi"].iloc[-1]

    macd_val = df["macd"].iloc[-1]
    macd_signal = df["macd_signal"].iloc[-1]

    volume = df["volume"].iloc[-1]
    volume_prev = df["volume"].iloc[-2]

    signal = False

    # شروط الإشارة
    if price > ema20 and ema20 > ema50 and rsi > 50 and macd_val > macd_signal and volume > volume_prev:

        signal = True

    if signal:

        entry = price

        tp1 = price * 1.03
        tp2 = price * 1.06
        tp3 = price * 1.10

        sl = price * 0.97

        message = f"""
🚀 Crypto Signal

Coin: {symbol}

Current Price: {price:.4f}

Entry: {entry:.4f}

🎯 Targets
TP1: {tp1:.4f}
TP2: {tp2:.4f}
TP3: {tp3:.4f}

🛑 Stop Loss
{sl:.4f}
"""

        send_telegram(message)

# تشغيل البوت
def run_bot():

    send_telegram("✅ Crypto Signal Bot Started")

    last_heartbeat = time.time()

    while True:

        for coin in coins:

            try:
                analyze(coin)

            except Exception as e:
                print(e)

        # رسالة كل ساعة
        if time.time() - last_heartbeat > 3600:

            send_telegram("🤖 Bot running normally")

            last_heartbeat = time.time()

        time.sleep(300)

run_bot()
