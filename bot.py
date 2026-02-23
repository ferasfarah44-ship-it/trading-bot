import ccxt
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime
import logging
import schedule
import os
import sys
from dotenv import load_dotenv

# إعداد التسجيل لمراقبة العمليات
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.FileHandler('trading_bot.log'), logging.StreamHandler(sys.stdout)]
)

# الإعدادات مع تخفيف الشروط (Relaxed Conditions)
CONFIG = {
    'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
    'ma_fast': 7,      # الخط الأصفر
    'ma_medium': 25,   # الخط البنفسجي
    'min_volume_ratio': 0.4, # شرط مخفف جداً للسيولة
    'max_rsi': 92,     # سماح حتى لو الزخم مرتفع
    'min_rsi': 30,     # استبعاد العملات الميتة فقط
    'scan_interval_minutes': 5
}

class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message):
        try:
            url = f"{self.base_url}/sendMessage"
            data = {'chat_id': self.chat_id, 'text': message, 'parse_mode': "HTML"}
            requests.post(url, json=data, timeout=10)
            return True
        except Exception as e:
            logging.error(f"Telegram Error: {e}")
            return False

class BinanceScanner:
    def __init__(self, config):
        self.config = config
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.telegram = TelegramNotifier(config['telegram_bot_token'], config['telegram_chat_id'])
    
    def get_data(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
            # حساب المتوسطات المطلوبة
            df['MA7'] = df['close'].rolling(window=self.config['ma_fast']).mean()
            df['MA25'] = df['close'].rolling(window=self.config['ma_medium']).mean()
            # حساب RSI لتجنب المناطق المتطرفة فقط
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + gain/loss))
            df['vol_avg'] = df['volume'].rolling(window=20).mean()
            return df
        except:
            return None

    def check_signal(self, symbol, df):
        if len(df) < 30: return None
        
        curr = df.iloc[-1]    # الشمعة الحالية
        prev = df.iloc[-2]    # الشمعة السابقة
        old = df.iloc[-3]     # الشمعة قبل السابقة
        
        # --- الشرط الجوهري: تقاطع MA7 صعوداً فوق MA25 ---
        # الأصفر الآن فوق البنفسجي
        is_above = curr['MA7'] > curr['MA25']
        # كان الأصفر تحت أو يساوي البنفسجي في أي من الشمعتين الماضيتين (بداية التقاطع)
        was_below = (prev['MA7'] <= prev['MA25']) or (old['MA7'] <= old['MA25'])
        
        cross_signal = is_above and was_below
        
        # --- الفلاتر المخففة (حتى لا تضيع الفرصة) ---
        rsi_ok = self.config['min_rsi'] < curr['RSI'] < self.config['max_rsi']
        vol_ok = curr['volume'] > (curr['vol_avg'] * self.config['min_volume_ratio'])

        if cross_signal and rsi_ok and vol_ok:
            return {
                'price': curr['close'],
                'rsi': curr['RSI'],
                'ma7': curr['MA7'],
                'ma25': curr['MA25']
            }
        return None

    def run_scan(self):
        logging.info("🔎 فحص التقاطعات الجارية...")
        try:
            markets = self.exchange.load_markets()
            pairs = [s for s in markets.keys() if s.endswith('/USDT') and not s.startswith('1000')]
            
            for symbol in pairs[:150]: # فحص أهم العملات لضمان السرعة
                df = self.get_data(symbol)
                if df is None: continue
                
                sig = self.check_signal(symbol, df)
                if sig:
                    msg = f"🚀 <b>إشارة تقاطع MA7/MA25</b>\n\n" \
                          f"العملة: <b>{symbol}</b>\n" \
                          f"السعر الحالي: <code>{sig['price']:.6f}</code>\n" \
                          f"الأصفر (MA7): {sig['ma7']:.6f}\n" \
                          f"البنفسجي (MA25): {sig['ma25']:.6f}\n" \
                          f"مؤشر RSI: {sig['rsi']:.1f}"
                    self.telegram.send_message(msg)
                    logging.info(f"✅ تم إرسال إشارة: {symbol}")
        except Exception as e:
            logging.error(f"Scan Error: {e}")

    def start(self):
        self.telegram.send_message("🤖 <b>تم تشغيل بوت التقاطعات</b>\nيتم الفحص بناءً على استراتيجية MA7/MA25.")
        self.run_scan()
        schedule.every(self.config['scan_interval_minutes']).minutes.do(self.run_scan)
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    scanner = BinanceScanner(CONFIG)
    scanner.start()
