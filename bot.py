import time
import requests
import pandas as pd

TELEGRAM_TOKEN = "8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE"
CHAT_ID = "7960335113"

COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=150"
    data = requests.get(url).json()

    df = pd.DataFrame(data)
    df = df.iloc[:, :6]
    df.columns = ['time','open','high','low','close','volume']
    df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)

    return df

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text
    })

def analyze(symbol):
    df = get_klines(symbol)

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['rsi'] = calculate_rsi(df)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if prev['ema9'] < prev['ema21'] and last['ema9'] > last['ema21'] and last['rsi'] > 50:

        entry = last['close']
        resistance = df['high'].tail(20).max()
        support = df['low'].tail(20).min()

        target = resistance
        stop_loss = support

        rr = round((target - entry) / (entry - stop_loss), 2) if entry != stop_loss else 0

        message = (
            f"🚀 Signal {symbol}\n\n"
            f"Entry: {round(entry,6)}\n"
            f"Target: {round(target,6)}\n"
            f"Stop Loss: {round(stop_loss,6)}\n"
            f"RSI: {round(last['rsi'],2)}\n"
            f"R/R: {rr}"
        )

        return message

    return None


if __name__ == "__main__":
    send_msg("Bot started successfully - 5m scalping mode")
    last_ping = time.time()

    while True:
        try:
            for coin in COINS:
                signal = analyze(coin)
                if signal:
                    send_msg(signal)

            if time.time() - last_ping >= 3600:
                send_msg("Bot is running normally.")
                last_ping = time.time()

            time.sleep(300)

        except Exception as e:
            send_msg(f"Error: {e}")
            time.sleep(60)
