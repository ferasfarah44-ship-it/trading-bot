import os
import time
import requests
import pandas as pd
from binance.client import Client

# إعدادات البيئة (سيتم ضبطها في Railway)
API_KEY = os.getenv('BINANCE_API_KEY', '') # اختيارية للبيانات العامة
API_SECRET = os.getenv('BINANCE_API_SECRET', '')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

client = Client(API_KEY, API_SECRET)

def send_telegram_msg(message):
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_data(symbol):
    # جلب آخر 100 شمعة بإطار زمن 15 دقيقة (كما في الصورة)
    candles = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
    df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'q_vol', 'trades', 'takers_buy_base', 'takers_buy_quote', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])
    return df

def analyze():
    # جلب قائمة العملات مقابل USDT فقط
    info = client.get_exchange_info()
    symbols = [s['symbol'] for s in info['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
    
    print(f"Analyzing {len(symbols)} pairs...")
    
    for symbol in symbols:
        try:
            df = get_data(symbol)
            # حساب المتوسط المتحرك (الخط الأصفر - مثلاً MA7)
            df['MA_fast'] = df['close'].rolling(window=7).mean()
            # حساب متوسط أبطأ للتأكيد (مثلاً MA25)
            df['MA_slow'] = df['close'].rolling(window=25).mean()
            
            last_price = df['close'].iloc[-1]
            ma_fast = df['MA_fast'].iloc[-1]
            ma_slow = df['MA_slow'].iloc[-1]
            
            # شرط التقاطع: الخط الأصفر (السريع) يصعد فوق البطئ
            if ma_fast > ma_slow and df['MA_fast'].iloc[-2] <= df['MA_slow'].iloc[-2]:
                target1 = last_price * 1.02 # هدف أول 2%
                target2 = last_price * 1.05 # هدف ثاني 5%
                
                msg = (f"🚀 **إشارة دخول جديدة!**\n\n"
                       f"💎 العملة: #{symbol}\n"
                       f"💰 سعر الدخول: {last_price}\n"
                       f"🎯 الأهداف:\n"
                       f"1️⃣ {target1:.4f}\n"
                       f"2️⃣ {target2:.4f}\n"
                       f"⚠️ وقف الخسارة: {last_price * 0.97:.4f}")
                
                send_telegram_msg(msg)
                print(f"Signal sent for {symbol}")
                
        except Exception as e:
            continue

if __name__ == "__main__":
    while True:
        analyze()
        time.sleep(900) # فحص كل 15 دقيقة
