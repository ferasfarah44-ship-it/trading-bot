import ccxt
import pandas as pd
import time
import requests
import logging
import schedule
import os
import sys
from dotenv import load_dotenv

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
        except Exception as e:
            logging.error(f"Telegram Error: {e}")

class BinanceScanner:
    def __init__(self, config):
        self.config = config
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.telegram = TelegramNotifier(
            config['telegram_bot_token'],
            config['telegram_chat_id']
        )
    
    def get_data(self, symbol):
        try:
            # فريم 15 دقيقة
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])

            df['MA7'] = df['close'].rolling(window=self.config['ma_fast']).mean()
            df['MA25'] = df['close'].rolling(window=self.config['ma_medium']).mean()

            return df
        except:
            return None

    def check_signal(self, symbol, df):
        if len(df) < 30:
            return None
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        old = df.iloc[-3]

        # 🔹 شرط التقاطع
        cross_up = (curr['MA7'] > curr['MA25']) and (prev['MA7'] <= prev['MA25'])

        # 🔹 شرط ارتفاع الأصفر (3 شموع متتالية صاعدة)
        ma7_rising = curr['MA7'] > prev['MA7'] > old['MA7']

        if cross_up or ma7_rising:
            return {
                'price': curr['close'],
                'ma7': curr['MA7'],
                'ma25': curr['MA25']
            }

        return None

    def run_scan(self):
        logging.info("🔎 فحص تقاطع أو ارتفاع MA7 (15م)...")

        try:
            markets = self.exchange.load_markets()
            pairs = [s for s in markets.keys() if s.endswith('/USDT')]

            for symbol in pairs:
                df = self.get_data(symbol)
                if df is None:
                    continue
                
                sig = self.check_signal(symbol, df)
                if sig:
                    msg = (
                        f"🚀 <b>إشارة MA7 (تقاطع أو ارتفاع)</b>\n\n"
                        f"العملة: <b>{symbol}</b>\n"
                        f"السعر: <code>{sig['price']:.6f}</code>\n"
                        f"MA7: {sig['ma7']:.6f}\n"
                        f"MA25: {sig['ma25']:.6f}"
                    )
                    self.telegram.send_message(msg)
                    logging.info(f"✅ إشارة: {symbol}")

        except Exception as e:
            logging.error(f"Scan Error: {e}")

    def start(self):
        self.telegram.send_message("🤖 تم تشغيل بوت تقاطع أو ارتفاع MA7 (15م)")
        self.run_scan()
        schedule.every(self.config['scan_interval_minutes']).minutes.do(self.run_scan)

        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    scanner = BinanceScanner(CONFIG)
    scanner.start()
