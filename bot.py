import os
import time
import schedule
import telebot
import pandas as pd
import ccxt

# جلب توكن تلجرام ومعرف الشات من إعدادات Railway
TELE_TOKEN = os.getenv('8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE')
CHAT_ID = os.getenv('7960335113')
bot = telebot.TeleBot(TELE_TOKEN)

# تهيئة الاتصال بالسوق (بيانات عامة بدون API Key)
exchange = ccxt.binance()

def get_top_150_pairs():
    """جلب قائمة بأكثر 150 زوجاً تداولاً مقابل USDT"""
    try:
        tickers = exchange.fetch_tickers()
        usdt_pairs = [symbol for symbol in tickers if symbol.endswith('/USDT')]
        # ترتيب العملات حسب حجم التداول التنازلي واختيار أول 150
        sorted_pairs = sorted(usdt_pairs, key=lambda x: tickers[x]['quoteVolume'], reverse=True)
        return sorted_pairs[:150]
    except Exception as e:
        print(f"Error fetching pairs: {e}")
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

def analyze_pair(symbol):
    """تحليل العملة بناءً على تقاطع الخط الأصفر للأعلى"""
    try:
        # جلب البيانات بفريم الساعة (1h)
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المتوسطات (الأصفر 7 والآخر 25)
        df['ma_short'] = df['close'].rolling(window=7).mean()
        df['ma_long'] = df['close'].rolling(window=25).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # شرط التقاطع للأعلى (الخط الأصفر يقطع للأعلى)
        if prev['ma_short'] < prev['ma_long'] and last['ma_short'] > last['ma_long']:
            price = last['close']
            msg = (f"🚀 **إشارة دخول (فريم الساعة): {symbol}**\n\n"
                   f"💰 السعر الحالي: {price}\n"
                   f"📥 سعر الدخول: {price}\n\n"
                   f"🎯 الهدف 1: {round(price * 1.03, 5)}\n"
                   f"🎯 الهدف 2: {round(price * 1.05, 5)}\n"
                   f"🎯 الهدف 3: {round(price * 1.10, 5)}\n"
                   f"🛠 التحليل: الخط الأصفر اخترق للأعلى")
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    except:
        pass

def run_scanner():
    """بدء مسح الـ 150 زوجاً"""
    pairs = get_top_150_pairs()
    for pair in pairs:
        analyze_pair(pair)
        time.sleep(0.1) # لتجنب الضغط على السيرفر

def send_status():
    """رسالة الحالة كل ساعة"""
    bot.send_message(CHAT_ID, "✅ تحديث: البوت والتحليل (فريم الساعة) يعملان بنجاح على 150 زوجاً.")

# رسائل البداية والجدولة
bot.send_message(CHAT_ID, "🤖 تم تشغيل البوت! جاري مسح 150 زوجاً مقابل USDT على فريم الساعة.")

# جدولة المهام
schedule.every(20).minutes.do(run_scanner) # إعادة المسح كل 20 دقيقة (مناسب لفريم الساعة)
schedule.every(1).hours.do(send_status)    # رسالة التأكيد كل ساعة

if __name__ == "__main__":
    # تشغيل المسح الأول فوراً عند التشغيل
    run_scanner()
    while True:
        schedule.run_pending()
        time.sleep(1)
