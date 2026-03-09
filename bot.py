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
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telegram.Bot(token=TOKEN)

# قائمة العملات
cryptocurrencies = [
'BTC/USDT','ETH/USDT','BNB/USDT','SOL/USDT','XRP/USDT',
'ADA/USDT','AVAX/USDT','DOT/USDT','MATIC/USDT','LINK/USDT',
'ATOM/USDT','NEAR/USDT','APT/USDT','ARBUSDT','OP/USDT',
'INJ/USDT','SUI/USDT','SEI/USDT','FTM/USDT','FIL/USDT'
]

# اتصال Binance
exchange = ccxt.binance()

# جلب البيانات
def get_ohlcv(symbol, timeframe='1h', limit=100):

    try:

        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

        df = pd.DataFrame(
            bars,
            columns=['timestamp','open','high','low','close','volume']
        )

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        return df

    except Exception as e:

        print(f"خطأ في {symbol}", e)

        return None


# تحليل السوق
def analyze_market(symbol):

    df = get_ohlcv(symbol)

    if df is None or df.empty:
        return None

    close = df['close']
    high = df['high']
    volume = df['volume']

    ema20 = EMAIndicator(close=close, window=20).ema_indicator()

    rsi = RSIIndicator(close=close, window=14).rsi()

    macd = MACD(close=close)

    macd_line = macd.macd()

    signal_line = macd.macd_signal()

    last_close = close.iloc[-1]

    last_ema20 = ema20.iloc[-1]

    last_rsi = rsi.iloc[-1]

    last_macd = macd_line.iloc[-1]

    last_signal = signal_line.iloc[-1]

    resistance = high.rolling(20).max().iloc[-2]

    last_volume = volume.iloc[-1]

    avg_volume = volume.rolling(20).mean().iloc[-1]

    return {
        'close': last_close,
        'ema20': last_ema20,
        'rsi': last_rsi,
        'macd': last_macd,
        'signal': last_signal,
        'resistance': resistance,
        'volume': last_volume,
        'avg_volume': avg_volume
    }


# فحص الشروط
def check_conditions(data):

    conditions = []

    if data['close'] > data['ema20']:
        conditions.append('السعر فوق EMA20')

    if data['rsi'] > 50:
        conditions.append('RSI فوق 50')

    if data['macd'] > data['signal']:
        conditions.append('MACD صاعد')

    if data['close'] > data['resistance']:
        conditions.append('اختراق مقاومة')

    if data['volume'] > data['avg_volume'] * 1.5:
        conditions.append('زيادة حجم التداول')

    return conditions


# ارسال رسالة
def send_message(text):

    try:

        bot.sendMessage(chat_id=CHAT_ID, text=text)

    except Exception as e:

        print("Telegram error", e)


# حساب الأهداف
def create_signal(symbol, data):

    entry = data['close']

    tp1 = entry * 1.02

    tp2 = entry * 1.04

    tp3 = entry * 1.06

    sl = entry * 0.97

    message = f"""
🚀 إشارة تداول

العملة: {symbol}

الدخول: {entry}

🎯 الهدف1: {tp1}
🎯 الهدف2: {tp2}
🎯 الهدف3: {tp3}

🛑 وقف الخسارة: {sl}
"""

    return message


# تشغيل البوت
last_hour = None

send_message("✅ تم تشغيل بوت الإشارات")

while True:

    now = datetime.datetime.now()

    # تحليل العملات
    for symbol in cryptocurrencies:

        data = analyze_market(symbol)

        if data:

            conditions = check_conditions(data)

            if len(conditions) >= 3:

                message = create_signal(symbol, data)

                send_message(message)

    # رسالة كل ساعة
    if now.hour != last_hour:

        last_hour = now.hour

        send_message("🤖 البوت يعمل بشكل طبيعي")

    time.sleep(300)
