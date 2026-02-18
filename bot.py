import os
import time
import requests
import pandas as pd
from binance.client import Client
from datetime import datetime

# --- المتغيرات ---
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_TOKEN = os.getenv('8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE')
CHAT_ID = os.getenv('7960335113')

# محاولة تجاوز حظر Railway باستخدام روابط API بديلة
client = Client(API_KEY, API_SECRET)
client.API_URL = 'https://api1.binance.com/api' # تجربة رابط api1 أو api2 أو api3

HALAL_COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # استخدام Markdown لجعل الخط مريح للقراءة
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    send_msg("🚀 *تم بدء تشغيل البوت بنجاح*")
    last_ping = time.time()

    while True:
        try:
            # الفحص كل 5 دقائق
            for coin in HALAL_COINS:
                ticker = client.get_symbol_ticker(symbol=coin)
                price = ticker['price']
                # هنا يمكنك إضافة تحليلك، سأرسل السعر كمثال بسيط
                # send_msg(f"📊 العملة: *{coin}*\n💰 السعر الحالي: `{price}`")

            # رسالة كل ساعة للتأكد أن البوت يعمل
            if time.time() - last_ping >= 3600:
                send_msg("🤖 *تحديث:* البوت مستمر في الفحص الدوري\.")
                last_ping = time.time()

            time.sleep(300) 
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)
