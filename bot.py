import time
import datetime
import os
import pandas as pd
import ccxt
import requests
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.trend import MACD

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

cryptocurrencies = [
'BTC/USDT','ETH/USDT','SOL/USDT','XRP/USDT','ADA/USDT',
'AVAX/USDT','DOT/USDT','LINK/USDT','ATOM/USDT','NEAR/USDT',
'APT/USDT','ARB/USDT','OP/USDT','INJ/USDT','SUI/USDT',
'SEI/USDT','FTM/USDT','FIL/USDT','POL/USDT'
]

exchange = ccxt.kucoin({
'enableRateLimit': True
})

markets = exchange.load_markets()


def send_message(text):

    try:

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        data = {
        "chat_id": CHAT_ID,
        "text": text
        }

        requests.post(url, data=data)

    except Exception as e:

        print("Telegram error:", e)


def get_ohlcv(symbol):

    try:

        if symbol not in markets:
            print(symbol,"غير موجود")
            return None

        bars = exchange.fetch_ohlcv(symbol,'1h',limit=50)

        df = pd.DataFrame(
        bars,
        columns=['timestamp','open','high','low','close','volume']
        )

        return df

    except Exception as e:

        print("خطأ",symbol,e)

        return None


def analyze(symbol):

    df = get_ohlcv(symbol)

    if df is None:
        return None

    close = df['close']

    ema20 = EMAIndicator(close=close,window=20).ema_indicator()

    rsi = RSIIndicator(close=close,window=14).rsi()

    macd = MACD(close=close)

    macd_line = macd.macd()
    signal_line = macd.macd_signal()

    data = {

    "price": close.iloc[-1],

    "ema": ema20.iloc[-1],

    "rsi": rsi.iloc[-1],

    "macd": macd_line.iloc[-1],

    "signal": signal_line.iloc[-1]

    }

    return data


def check_signal(data):

    score = 0

    if data["price"] > data["ema"]:
        score += 1

    if data["rsi"] > 50:
        score += 1

    if data["macd"] > data["signal"]:
        score += 1

    return score


send_message("✅ Crypto Signal Bot Started")

last_hour = None

while True:

    now = datetime.datetime.now()

    if now.minute % 5 == 0:

        for symbol in cryptocurrencies:

            data = analyze(symbol)

            if data:

                score = check_signal(data)

                if score >= 2:

                    message = f"""
🚀 فرصة تداول

العملة: {symbol}

السعر: {data['price']}
RSI: {round(data['rsi'],2)}
"""

                    send_message(message)

            time.sleep(2)

        time.sleep(300)


    if now.hour != last_hour:

        last_hour = now.hour

        send_message("🤖 البوت يعمل بشكل طبيعي")


    time.sleep(60)
