import os
import time
import requests
import pandas as pd
from binance.client import Client
from datetime import datetime

# إعدادات التليجرام (يجب ضبطها في متغيرات بيئة Railway)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# إنشاء عميل بينانس بدون مفاتيح (لجلب البيانات العامة فقط)
client = Client()

def send_telegram_msg(message):
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ في إرسال التليجرام: {e}")

def get_data(symbol):
    try:
        # جلب آخر 100 شمعة بإطار 15 دقيقة (بيانات عامة)
        candles = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'q_vol', 'trades', 'takers_buy_base', 'takers_buy_quote', 'ignore'])
        df['close'] = pd.to_numeric(df['close'])
        return df
    except:
        return None

def analyze_market():
    try:
        # جلب قائمة العملات مقابل USDT فقط
        info = client.get_exchange_info()
        symbols = [s['symbol'] for s in info['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
        
        for symbol in symbols:
            df = get_data(symbol)
            if df is None or len(df) < 30: continue
            
            # حساب المتوسط المتحرك (الخط الأصفر MA7) ومتوسط أبطأ (MA25)
            df['MA7'] = df['close'].rolling(window=7).mean()
            df['MA25'] = df['close'].rolling(window=25).mean()
            
            # شرط التقاطع الصعودي (الخط الأصفر يخترق الخط الأبطأ لأعلى)
            if df['MA7'].iloc[-1] > df['MA25'].iloc[-1] and df['MA7'].iloc[-2] <= df['MA25'].iloc[-2]:
                price = df['close'].iloc[-1]
                msg = (f"🚀 **فرصة تداول جديدة: {symbol}**\n"
                       f"💰 سعر الدخول: {price}\n"
                       f"🎯 هدف 1: {price * 1.02:.4f}\n"
                       f"🎯 هدف 2: {price * 1.05:.4f}\n"
                       f"🛑 وقف الخسارة: {price * 0.97:.4f}")
                send_telegram_msg(msg)
    except Exception as e:
        print(f"خطأ في التحليل: {e}")

if __name__ == "__main__":
    send_telegram_msg("✅ **بدأ البوت الدورة التشغيلية الآن.. جاري تحليل سوق USDT.**")
    
    last_hourly_check = time.time()
    
    while True:
        # رسالة تأكيد العمل كل ساعة
        if time.time() - last_hourly_check >= 3600:
            send_telegram_msg("🔔 **تنبيه ساعة:** البوت يعمل بنجاح ويقوم بفحص العملات.")
            last_hourly_check = time.time()

        analyze_market()
        
        # انتظار 10 دقائق قبل الفحص التالي لتجنب حظر IP
        time.sleep(600)
