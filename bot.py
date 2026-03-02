import os
import time
import requests

# إعدادات التنبيه
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOLS = ['SOLUSDT', 'ETHUSDT', 'OPUSDT', 'NEARUSDT', 'ARBUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT']

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
        print(f"إرسال لتليجرام: {res.status_code}")
    except Exception as e:
        print(f"خطأ تليجرام: {e}")

def get_data(symbol):
    # جلب سعر الإغلاق لآخر شمعتين (ساعة) للتحليل
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=2"
    res = requests.get(url).json()
    return float(res[0][4]), float(res[1][4]) # السعر السابق والحالي

def run_bot():
    print("🚀 البوت بدأ فحص السوق الآن...")
    send_msg("✅ تم تشغيل البوت بنجاح وهو يراقب العملات الآن.")
    
    while True:
        for symbol in SYMBOLS:
            try:
                old_price, current_price = get_data(symbol)
                print(f"فحص {symbol}: السعر الحالي {current_price}")
                
                # شرط دخول بسيط: إذا السعر الحالي أعلى من سعر الإغلاق السابق (صعود)
                if current_price > old_price:
                    target = current_price * 1.03
                    msg = f"📈 **إشارة دخول: {symbol}**\n💰 السعر: `{current_price}`\n🎯 الهدف (3%): `{target:.4f}`"
                    send_msg(msg)
            except Exception as e:
                print(f"خطأ في {symbol}: {e}")
        
        print("💤 انتظار 5 دقائق للفحص القادم...")
        time.sleep(300)

if __name__ == "__main__":
    run_bot()
