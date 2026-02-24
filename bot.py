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

# إعداد التسجيل
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.FileHandler('trading_bot.log'), logging.StreamHandler(sys.stdout)]
)

CONFIG = {
    'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
    'ma_fast': 7,
    'ma_medium': 25,
    'min_rsi': 35,
    'max_rsi': 85,
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
            # ✅ فريم 15 دقيقة
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=120)
            df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])

            df['MA7'] = df['close'].rolling(window=self.config['ma_fast']).mean()
            df['MA25'] = df['close'].rolling(window=self.config['ma_medium']).mean()

            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + gain/loss))

            df['vol_avg'] = df['volume'].rolling(window=20).mean()

            return df
        except:
            return None

    def check_signal(self, symbol, df):
        if len(df) < 30:
            return None
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        old = df.iloc[-3]

        # ✅ تقاطع
        is_above = curr['MA7'] > curr['MA25']
        was_below = (prev['MA7'] <= prev['MA25']) or (old['MA7'] <= old['MA25'])
        cross_signal = is_above and was_below

        # ✅ ميل MA7 صاعد
        ma7_slope_up = curr['MA7'] > prev['MA7'] > old['MA7']

        # ✅ فوليوم أقوى من المتوسط
        vol_ok = curr['volume'] > curr['vol_avg']

        # ✅ كسر قمة آخر 5 شموع
        recent_high = df['high'].iloc[-6:-1].max()
        breakout = curr['close'] > recent_high

        # ✅ فلتر RSI
        rsi_ok = self.config['min_rsi'] < curr['RSI'] < self.config['max_rsi']

        if cross_signal and ma7_slope_up and vol_ok and breakout and rsi_ok:
            return {
                'price': curr['close'],
                'rsi': curr['RSI'],
                'ma7': curr['MA7'],
                'ma25': curr['MA25']
            }

        return None

    def run_scan(self):
        logging.info("🔎 فحص أقوى فرص سبوت 15م...")
        try:
            markets = self.exchange.load_markets()
            pairs = [s for s in markets.keys() if s.endswith('/USDT') and not s.startswith('1000')]

            signals = []

            for symbol in pairs[:200]:
                df = self.get_data(symbol)
                if df is None:
                    continue
                
                sig = self.check_signal(symbol, df)
                if sig:
                    strength = df.iloc[-1]['volume'] / df.iloc[-1]['vol_avg']
                    signals.append((symbol, sig, strength))

            # ✅ اختيار أقوى 3 حسب قوة الفوليوم
            top_signals = sorted(signals, key=lambda x: x[2], reverse=True)[:3]

            for symbol, sig, strength in top_signals:
                msg = (
                    f"🚀 <b>أقوى فرصة سبوت 15م</b>\n\n"
                    f"العملة: <b>{symbol}</b>\n"
                    f"السعر: <code>{sig['price']:.6f}</code>\n"
                    f"MA7: {sig['ma7']:.6f}\n"
                    f"MA25: {sig['ma25']:.6f}\n"
                    f"RSI: {sig['rsi']:.1f}\n"
                    f"قوة الفوليوم: {strength:.2f}x\n"
                    f"\n🎯 الهدف: 3–5%"
                )
                self.telegram.send_message(msg)
                logging.info(f"✅ تم إرسال إشارة قوية: {symbol}")

        except Exception as e:
            logging.error(f"Scan Error: {e}")

    def start(self):
        self.telegram.send_message("🤖 <b>تم تشغيل بوت أقوى 3 فرص سبوت (15م)</b>")
        self.run_scan()
        schedule.every(self.config['scan_interval_minutes']).minutes.do(self.run_scan)

        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    scanner = BinanceScanner(CONFIG)
    scanner.start()
