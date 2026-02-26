import os
import time
import requests
import pandas as pd
from binance.client import Client

# إعدادات التليجرام من Railway Variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# استخدام البيانات العامة بدون مفاتيح API
client = Client()

def send_telegram_msg(message):
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

def get_data(symbol):
    try:
        # جلب شمعات الـ 15 دقيقة
        candles = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'q_vol', 'trades', 'takers_buy_base', 'takers_buy_quote', 'ignore'])
        df['close'] = pd.to_numeric(df['close'])
        return df
    except:
        return None

def main_loop():
    send_telegram_msg("✅ **تم بدء الدورة التشغيلية بنجاح!**")
    last_status_time = time.time()
    
    while True:
        try:
            # رسالة التأكيد كل ساعة
            if time.time() - last_status_time >= 3600:
                send_telegram_msg("🔔 **تنبيه:** البوت يعمل ويحلل السوق الآن.")
                last_status_time = time.time()

            # جلب العملات المتاحة
            info = client.get_exchange_info()
            symbols = [s['symbol'] for s in info['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
            
            for symbol in symbols:
                df = get_data(symbol)
                if df is None or len(df) < 30: continue
                
                # تحليل المتوسطات (الخط الأصفر MA7)
                df['MA7'] = df['close'].rolling(window=7).mean()
                df['MA25'] = df['close'].rolling(window=25).mean()
                
                # شرط التقاطع الصعودي
                if df['MA7'].iloc[-1] > df['MA25'].iloc[-1] and df['MA7'].iloc[-2] <= df['MA25'].iloc[-2]:
                    price = df['close'].iloc[-1]
                    msg = (f"🚀 **فرصة تداول: {symbol}**\n"
                           f"💰 الدخول: {price}\n"
                           f"🎯 هدف 1: {price * 1.02:.4f}\n"
                           f"🎯 هدف 2: {price * 1.05:.4f}\n"
                           f"🛑 وقف: {price * 0.97:.4f}")
                    send_telegram_msg(msg)
            
            # انتظار 10 دقائق لتجنب الحظر
            time.sleep(600)
            
        except Exception as e:
            print(f"Error in Loop: {e}")
            time.sleep(60) # الانتظار دقيقة قبل إعادة المحاولة عند حدوث خطأ

if __name__ == "__main__":
    main_loop()
