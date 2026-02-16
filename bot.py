import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
import os
from datetime import datetime

# --- الإعدادات ---
TELEGRAM_TOKEN = os.getenv("8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE")
CHAT_ID = os.getenv("7960335113")
exchange = ccxt.binance({'enableRateLimit': True})

# متغير لتتبع وقت إرسال رسالة الحالة (Heartbeat)
last_heartbeat = 0 

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "MarkdownV2"} # استخدمنا النسخة الثانية للتنسيق الأفضل
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

def format_msg(symbol, price, tp1, tp2, sl, rsi):
    # تنسيق الرسالة ليكون مريحاً للعين وواضحاً جداً
    # ملاحظة: في MarkdownV2 يجب وضع علامة \ قبل النقطة والشرطة
    msg = (
        f"💎 *فرصة تداول جديدة: {symbol.replace('/', '\\/')}*\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 *سعر الدخول:* `{price:.5f}`\n\n"
        f"🎯 *الهدف الأول:* `{tp1:.5f}`\n"
        f"🔥 *الهدف الثاني:* `{tp2:.5f}`\n"
        f"🛑 *وقف الخسارة:* `{sl:.5f}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 *RSI:* `{rsi:.2f}`  |  🕒 `{datetime.now().strftime('%H:%M')}`"
    )
    return msg

def analyze_market():
    try:
        exchange.load_markets()
        symbols = [s for s in exchange.symbols if '/USDT' in s and exchange.markets[s]['active']]
        
        for symbol in symbols:
            if 'UP/' in symbol or 'DOWN/' in symbol: continue
            
            # تحليل العملة (نفس المنطق السابق)
            bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['RSI'] = df.ta.rsi(length=14)
            df['ATR'] = df.ta.atr(length=14)
            bb = df.ta.bbands(length=20, std=2)
            df = pd.concat([df, bb], axis=1)

            last = df.iloc[-1]
            if last['close'] > last['BBU_20_2.0'] and last['RSI'] > 60:
                atr = last['ATR']
                msg = format_msg(
                    symbol, last['close'], 
                    last['close'] + (atr * 1.5), 
                    last['close'] + (atr * 3), 
                    last['close'] - (atr * 1.5), 
                    last['RSI']
                )
                send_telegram_msg(msg)
            
            time.sleep(0.1) # حماية الـ API
    except Exception as e:
        print(f"Error during scan: {e}")

# --- تشغيل البوت ---
print("🚀 البوت بدأ الفحص المتواصل...")

while True:
    # 1. فحص السوق بالكامل
    analyze_market()
    
    # 2. تفقد هل مرّت ساعة لإرسال رسالة الحالة؟
    current_time = time.time()
    if current_time - last_heartbeat >= 3600:
        status_text = f"✅ *تحديث:* البوت يفحص السوق الآن بانتظام\n🕒 الوقت: `{datetime.now().strftime('%H:%M')}`"
        send_telegram_msg(status_text)
        last_heartbeat = current_time
    
    # تأخير بسيط جداً قبل الدورة التالية للفحص الشامل
    time.sleep(10)
