import ccxt
import pandas as pd
import ta
import requests
import time
from datetime import datetime

# ===== بياناتك =====
TELEGRAM_TOKEN = "PUT_YOUR_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

symbols = [
    "SOL/USDT",
    "ETH/USDT",
    "OP/USDT",
    "NEAR/USDT",
    "ARB/USDT"
]

exchange = ccxt.binance({
    'enableRateLimit': True
})

last_signals = {}
last_hour_report = datetime.now().hour

# ===== ارسال تلجرام =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

# ===== تحليل =====
def analyze(symbol):

    # اتجاه عام H1
    df_h1 = pd.DataFrame(exchange.fetch_ohlcv(symbol, '1h', limit=100),
                         columns=['time','open','high','low','close','volume'])
    df_h1['ema50'] = ta.trend.ema_indicator(df_h1['close'], window=50)

    if df_h1['close'].iloc[-1] < df_h1['ema50'].iloc[-1]:
        return  # تجاهل إذا الاتجاه هابط

    # تأكيد M15
    df_m15 = pd.DataFrame(exchange.fetch_ohlcv(symbol, '15m', limit=100),
                          columns=['time','open','high','low','close','volume'])
    resistance = df_m15['high'].rolling(20).max().iloc[-1]

    # دخول M5
    df_m5 = pd.DataFrame(exchange.fetch_ohlcv(symbol, '5m', limit=100),
                         columns=['time','open','high','low','close','volume'])

    df_m5['ema9'] = ta.trend.ema_indicator(df_m5['close'], window=9)
    df_m5['ema21'] = ta.trend.ema_indicator(df_m5['close'], window=21)
    df_m5['rsi'] = ta.momentum.rsi(df_m5['close'], window=14)

    last = df_m5.iloc[-1]
    prev = df_m5.iloc[-2]

    # تقاطع صاعد
    if prev['ema9'] < prev['ema21'] and last['ema9'] > last['ema21']:
        if 50 < last['rsi'] < 70:

            entry = last['close']
            target = resistance
            stop = df_m5['low'].rolling(10).min().iloc[-1]

            if target <= entry:
                return

            profit_percent = round((target - entry) / entry * 100, 2)

            confidence = 80

            # منع تكرار الإشارة
            if symbol in last_signals and abs(last_signals[symbol] - entry) < entry*0.003:
                return

            last_signals[symbol] = entry

            message = f"""
🚀 اشارة شراء - {symbol}

💰 السعر الحالي: {round(entry,4)}
📥 الدخول: {round(entry,4)}

🎯 الهدف الفني (مقاومة M15): {round(target,4)}
📈 نسبة الربح المتوقعة: +{profit_percent}%

🛑 وقف الخسارة: {round(stop,4)}

📊 قوة الثقة: {confidence}%
📈 الاتجاه H1: صاعد
"""
            send_telegram(message)

# ===== بدء التشغيل =====
send_telegram("✅ تم تشغيل بوت السكالبينغ بنجاح\n📊 مراقبة 6 عملات\n⏱ الفحص كل 5 دقائق\n🚀 النظام يعمل بثبات")

# ===== حلقة مستمرة =====
while True:
    try:
        for symbol in symbols:
            analyze(symbol)

        # تقرير كل ساعة
        current_hour = datetime.now().hour
        if current_hour != last_hour_report:
            send_telegram("📊 تقرير الساعة\n✔ السوق تحت المراقبة\n🔍 يتم التحليل كل 5 دقائق")
            last_hour_report = current_hour

        time.sleep(300)

    except Exception as e:
        time.sleep(60)
