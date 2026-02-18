import os
import time
import requests
import pandas as pd
import pandas_ta as ta
from binance.client import Client
from datetime import datetime

# --- الإعدادات من Variables ---
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_TOKEN = os.getenv('8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE')
CHAT_ID = os.getenv('7960335113')

# محاولة تجاوز حظر الموقع باستخدام رابط بديل
client = Client(API_KEY, API_SECRET)
client.API_URL = 'https://api1.binance.com/api' 

# قائمة العملات المتوافقة (حسب تفضيلك السابق)
HALAL_COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # التنسيق MarkdownV2 يجعل الخط عريضاً والأرقام واضحة
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "MarkdownV2"}
    try:
        requests.post(url, json=payload)
    except:
        pass

def get_signal(symbol):
    try:
        bars = client.get_klines(symbol=symbol, interval='15m', limit=100)
        df = pd.DataFrame(bars, columns=['date','open','high','low','close','vol','ct','qa','nt','tb','tq','i'])
        df['close'] = df['close'].astype(float)
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        current_price = df['close'].iloc[-1]
        rsi_val = df['RSI'].iloc[-1]

        # شرط دخول بسيط (تشبع بيعي)
        if rsi_val < 35:
            return {
                "entry": current_price,
                "t1": current_price * 1.02,
                "sl": current_price * 0.98
            }
        return None
    except:
        return None

if __name__ == "__main__":
    send_telegram("🚀 *تم بدء تشغيل البوت بنجاح*")
    
    last_heartbeat = time.time()
    
    while True:
        try:
            # فحص كل 5 دقائق
            for coin in HALAL_COINS:
                data = get_signal(coin)
                if data:
                    # تنسيق مريح للعين مع معالجة النقاط لتناسب تلجرام
                    entry = str(data['entry']).replace('.', '\.')
                    msg = f"✅ *إشارة جديدة: {coin}*\n💰 السعر: `{entry}`"
                    send_telegram(msg)
            
            # رسالة كل ساعة للتأكد أن البوت يعمل
            if time.time() - last_heartbeat >= 3600:
                send_telegram("🤖 *تحديث:* البوت ما زال يعمل ويفحص السوق\.")
                last_heartbeat = time.time()
                
            time.sleep(300) # انتظار 5 دقائق
        except Exception as e:
            time.sleep(60)
