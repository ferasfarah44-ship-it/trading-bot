import time
import datetime
import os
import pandas as pd
import ccxt
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.trend import MACD
import telegram

# إعدادات التليجرام
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TOKEN)

# العملات القوية
cryptocurrencies = [

'BTC/USDT',
'ETH/USDT',
'SOL/USDT',
'XRP/USDT',
'ADA/USDT',
'AVAX/USDT',
'DOT/USDT',
'LINK/USDT',
'ATOM/USDT',
'NEAR/USDT',
'APT/USDT',
'ARB/USDT',
'OP/USDT',
'INJ/USDT',
'SUI/USDT',
'SEI/USDT',
'FIL/USDT',
'POL/USDT'

]

# منصة التداول
exchange = ccxt.kucoin({
'enableRateLimit': True
})

markets = exchange.load_markets()

# ارسال رسالة تلجرام
def send_message(text):

    try:

        bot.send_message(
            chat_id=CHAT_ID,
            text=text
        )

        print("Telegram message sent")

    except Exception as e:

        print("Telegram Error:", e)


# جلب بيانات الشموع
def get_ohlcv(symbol):

    try:

        if symbol not in markets:

            print(symbol, "غير موجود")
            return None

        bars = exchange.fetch_ohlcv(
            symbol,
            timeframe='1h',
            limit=50
        )

        df = pd.DataFrame(
            bars,
            columns=[
                'timestamp',
                'open',
                'high',
                'low',
                'close',
                'volume'
            ]
        )

        df['timestamp'] = pd.to_datetime(
            df['timestamp'],
            unit='ms'
        )

        return df

    except Exception as e:

        print("خطأ في", symbol, e)
        return None


# تحليل العملة
def analyze_market(symbol):

    df = get_ohlcv(symbol)

    if df is None:
        return None

    close = df['close']

    ema20 = EMAIndicator(
        close=close,
        window=20
    ).ema_indicator()

    rsi = RSIIndicator(
        close=close,
        window=14
    ).rsi()

    macd = MACD(close=close)

    macd_line = macd.macd()
    signal_line = macd.macd_signal()

    return {

        "close": close.iloc[-1],
        "ema20": ema20.iloc[-1],
        "rsi": rsi.iloc[-1],
        "macd": macd_line.iloc[-1],
        "signal": signal_line.iloc[-1]

    }


# شروط الاشارة
def check_conditions(data):

    conditions = []

    if data["close"] > data["ema20"]:
        conditions.append("السعر فوق EMA20")

    if data["rsi"] > 50:
        conditions.append("RSI فوق 50")

    if data["macd"] > data["signal"]:
        conditions.append("MACD صاعد")

    return conditions


# بدء البوت
send_message("✅ Crypto Signal Bot Started")

last_hour = None


while True:

    now = datetime.datetime.now()

    # تحليل كل 5 دقائق
    if now.minute % 5 == 0:

        print("بدأ التحليل")

        for symbol in cryptocurrencies:

            data = analyze_market(symbol)

            if data is None:
                continue

            conditions = check_conditions(data)

            if len(conditions) >= 2:

                message = f"""
🚀 فرصة تداول

العملة: {symbol}

السعر: {data['close']}

الشروط:
{chr(10).join(conditions)}
"""

                send_message(message)

            time.sleep(2)

        time.sleep(300)


    # رسالة كل ساعة
    if now.hour != last_hour:

        last_hour = now.hour

        send_message("🤖 البوت يعمل بشكل طبيعي")


    time.sleep(60)
