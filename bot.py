import os
import time
import requests
import pandas as pd
from binance.client import Client
from datetime import datetime

# --- الإعدادات (يفضل وضعها في Environment Variables في Railway) ---
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_TOKEN = os.getenv('8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE')
CHAT_ID = os.getenv('7960335113')

client = Client(API_KEY, API_SECRET)

# قائمة تقريبية للعملات (يمكنك تحديثها حسب الفلتر الشرعي الخاص بك)
HALAL_COINS = ['BTC', 'ETH', 'ADA', 'DOT', 'MATIC', 'SOL', 'ALGO', 'AVAX'] 

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" # لجعل الخط مرتباً وقابلًا للقراءة
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

def get_analysis(symbol):
    """تحليل بسيط للعملة لإعطاء سعر دخول وأهداف"""
    try:
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        close_prices = df['close'].astype(float)
        
        current_price = close_prices.iloc[-1]
        # استراتيجية بسيطة: الدخول عند السعر الحالي، الأهداف بناءً على نسبة مئوية
        entry_price = current_price
        target1 = entry_price * 1.02 # هدف 2%
        target2 = entry_price * 1.05 # هدف 5%
        stop_loss = entry_price * 0.97 # وقف 3%

        return entry_price, target1, target2, stop_loss
    except:
        return None

def scan_market():
    """البحث عن فرص في العملات المختارة"""
    findings = []
    for coin in HALAL_COINS:
        symbol = coin + "USDT"
        # هنا يمكنك إضافة شروط إضافية (مثل RSI أو حجم التداول)
        analysis = get_analysis(symbol)
        if analysis:
            entry, t1, t2, sl = analysis
            msg = (
                f"🚀 *فرصة جديدة: {coin}/USDT*\n\n"
                f"💰 *سعر الدخول:* `{entry:.4f}`\n"
                f"🎯 *الهدف الأول:* `{t1:.4f}`\n"
                f"🎯 *الهدف الثاني:* `{t2:.4f}`\n"
                f"🚫 *وقف الخسارة:* `{sl:.4f}`\n\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
            findings.append(msg)
    return findings

# --- الحلقة الرئيسية ---
if __name__ == "__main__":
    send_telegram_msg("✅ *تم تشغيل البوت بنجاح!*\nسيتم الفحص كل 5 دقائق وإرسال تقرير حالة كل ساعة.")
    
    last_heartbeat = time.time()
    
    while True:
        try:
            # 1. فحص الفرص كل 5 دقائق
            opportunities = scan_market()
            for op in opportunities:
                send_telegram_msg(op)
            
            # 2. رسالة الحالة كل ساعة (3600 ثانية)
            if time.time() - last_heartbeat >= 3600:
                send_telegram_msg("🤖 *تحديث الحالة:* البوت يعمل الآن ويراقب السوق بنشاط.")
                last_heartbeat = time.time()
                
            time.sleep(300) # انتظار 5 دقائق
            
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(60)
