import time
import datetime
import os
import pandas as pd
import ccxt
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.macd import MACD
import telegram

# إعدادات التليجرام من متغيرات بيئية
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telegram.Bot(token=TOKEN)

# قائمة العملات التي تريد مراقبتها
cryptocurrencies = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']  # يمكنك تعديلها

# إعدادات Binance بدون مفاتيح API
exchange = ccxt.binance()

# الدالة لجلب البيانات
def get_ohlcv(symbol, timeframe='1h', limit=50):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"خطأ في جلب البيانات لـ {symbol}: {e}")
        return None

# تحليل السوق
def analyze_market(symbol):
    df = get_ohlcv(symbol)
    if df is None or df.empty:
        return None
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    # حساب المؤشرات
    ema20 = EMAIndicator(close=close).ema_indicator()
    rsi = RSIIndicator(close=close, window=14).rsi()
    macd = MACD(close=close)
    macd_line = macd.macd()
    signal_line = macd.macd_signal()
    
    # آخر القيم
    last_close = close.iloc[-1]
    last_ema20 = ema20.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_macd = macd_line.iloc[-1]
    last_signal = signal_line.iloc[-1]
    
    return {
        'close': last_close,
        'ema20': last_ema20,
        'rsi': last_rsi,
        'macd': last_macd,
        'signal': last_signal
    }

# فحص الشروط
def check_conditions(data):
    conditions = []
    if data['close'] > data['ema20']:
        conditions.append('السعر أعلى من EMA20')
    if data['rsi'] > 50:
        conditions.append('RSI أعلى من 50')
    if data['macd'] > data['signal']:
        conditions.append('MACD يتقاطع من الأسفل للأعلى')
    return conditions

# إرسال رسالة
def send_message(text):
    bot.sendMessage(chat_id=CHAT_ID, text=text)

# الحلقة الرئيسية
last_hour = None
while True:
    now = datetime.datetime.now()
    
    # تحليل كل 5 دقائق لكل عملة
    if now.minute % 5 == 0:
        for symbol in cryptocurrencies:
            data = analyze_market(symbol)
            if data:
                conditions = check_conditions(data)
                if conditions:
                    msg = f"فرصة محتملة على {symbol}:\n" + "\n".join(conditions)
                    send_message(msg)
        time.sleep(300)  # انتظار 5 دقائق بعد كل تحليل

    # إرسال رسالة كل ساعة تؤكد أن البوت يعمل
    if now.hour != last_hour:
        last_hour = now.hour
        send_message("البوت يعمل بشكل صحيح.")

    time.sleep(60)
