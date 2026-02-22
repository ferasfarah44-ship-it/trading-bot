import ccxt
import pandas as pd
import time
import requests
from datetime import datetime, timedelta
import logging
import schedule
import os
import sys

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def validate_config():
    """Validate Telegram credentials"""
    print("=" * 60)
    print("🔍 VALIDATING CONFIGURATION")
    print("=" * 60)
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print(f"\n📱 TELEGRAM_BOT_TOKEN: {'✅ Found' if token else '❌ Missing'}")
    print(f"👤 TELEGRAM_CHAT_ID: {'✅ Found' if chat_id else '❌ Missing'}\n")
    
    if not token or token == 'None':
        print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing or invalid!")
        print("   Add it in Railway Variables section")
        return False
    
    if not chat_id or chat_id == 'None':
        print("❌ ERROR: TELEGRAM_CHAT_ID is missing or invalid!")
        print("   Add it in Railway Variables section")
        return False
    
    print("✅ Configuration valid!")
    return True

# Configuration
CONFIG = {
    'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
    'ma_periods': {'fast': 7, 'medium': 25, 'slow': 99, 'long': 200},
    'targets': {'tp1_percent': 3, 'tp2_percent': 6, 'tp3_percent': 10, 'stop_loss': 2},
    'scan_interval_minutes': 5
}

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message: str) -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': "HTML",
                'disable_web_page_preview': True
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            logging.info("✅ Telegram message sent")
            return True
        except Exception as e:
            logging.error(f"❌ Telegram error: {e}")
            return False
    
    def test_connection(self):
        msg = "🔊 <b>BOT TEST</b>\n\n✅ Connected!"
        return self.send_message(msg)

class BinanceScanner:
    def __init__(self, config):
        self.config = config
        self.exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
        self.telegram = TelegramNotifier(config['telegram_bot_token'], config['telegram_chat_id'])
        self.start_time = None
        self.signals_count = 0
        self.analyzed_pairs = set()
    
    def get_usdt_pairs(self):
        try:
            markets = self.exchange.load_markets()
            pairs = [s for s in markets.keys() if s.endswith('/USDT') and not s.startswith('1000')]
            return sorted(pairs)[:200]
        except Exception as e:
            logging.error(f"❌ Error getting pairs: {e}")
            return []
    
    def get_ohlcv_data(self, symbol, timeframe='1h', limit=300):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logging.error(f"❌ Error fetching {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        df['MA7'] = df['close'].rolling(window=7).mean()
        df['MA25'] = df['close'].rolling(window=25).mean()
        df['MA99'] = df['close'].rolling(window=99).mean()
        df['MA200'] = df['close'].rolling(window=200).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))
        df['volume_MA'] = df['volume'].rolling(window=20).mean()
        return df
    
    def check_signal(self, df):
        if len(df) < 200:
            return {'signal': False}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        ma7_cross = previous['MA7'] <= previous['MA25'] and current['MA7'] > current['MA25']
        price_above = current['close'] > current['MA7']
        ma7_up = current['MA7'] > previous['MA7']
        vol_spike = current['volume'] > (current['volume_MA'] * 1.5)
        rsi_ok = 30 < current['RSI'] < 70
        
        signal = (ma7_cross or (price_above and ma7_up)) and vol_spike and rsi_ok
        
        return {
            'signal': signal,
            'current_price': current['close'],
            'ma7': current['MA7'],
            'ma25': current['MA25'],
            'ma99': current['MA99'],
            'ma200': current['MA200'],
            'rsi': current['RSI'],
            'price_change_24h': ((current['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close']) * 100 if len(df) >= 24 else 0
        }
    
    def calculate_targets(self, price):
        return {
            'entry': price,
            'tp1': price * 1.03,
            'tp2': price * 1.06,
            'tp3': price * 1.10,
            'sl': price * 0.98
        }
    
    def format_message(self, symbol, data, targets):
        return f"""
🚀 <b>NEW SIGNAL!</b>

<b>Pair:</b> {symbol}
💰 <b>Price:</b> ${data['current_price']:.6f}

📈 <b>Indicators:</b>
├ MA7: ${data['ma7']:.6f}
├ MA25: ${data['ma25']:.6f}
├ RSI: {data['rsi']:.2f}
└ 24h: {data['price_change_24h']:+.2f}%

🎯 <b>Targets:</b>
├ TP1: ${targets['tp1']:.6f} (+3%)
├ TP2: ${targets['tp2']:.6f} (+6%)
├ TP3: ${targets['tp3']:.6f} (+10%)
└ SL: ${targets['sl']:.6f} (-2%)

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
    
    def run_scan(self):
        pairs = self.get_usdt_pairs()
        if not pairs:
            return 0
        
        logging.info(f"🔍 Scanning {len(pairs)} pairs...")
        found = 0
        
        for symbol in pairs:
            try:
                df = self.get_ohlcv_data(symbol)
                if df is None:
                    continue
                
                df = self.calculate_indicators(df)
                data = self.check_signal(df)
                
                if data['signal']:
                    targets = self.calculate_targets(data['current_price'])
                    msg = self.format_message(symbol, data, targets)
                    if self.telegram.send_message(msg):
                        found += 1
                        self.signals_count += 1
                        logging.info(f"🚀 Signal: {symbol}")
                
                self.analyzed_pairs.add(symbol)
                
            except Exception as e:
                logging.error(f"❌ Error {symbol}: {e}")
                continue
        
        logging.info(f"✅ Done. Found {found} signals")
        return found
    
    def send_startup(self):
        msg = f"""
🤖 <b>BOT STARTED</b>

✅ Running
📊 200 USDT pairs
📈 MA7 Strategy
⏱️ Every {CONFIG['scan_interval_minutes']} min

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.telegram.send_message(msg)
    
    def send_status(self):
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        msg = f"""
⏰ <b>STATUS</b>

✅ Running
⏳ {str(uptime).split('.')[0]}
📊 {len(self.analyzed_pairs)} pairs
📈 {self.signals_count} signals
"""
        return self.telegram.send_message(msg)
    
    def run(self):
        logging.info("🚀 Starting Bot...")
        self.start_time = datetime.now()
        
        if not self.telegram.test_connection():
            logging.error("❌ Telegram test failed!")
            return
        
        logging.info("✅ Telegram OK!")
        self.send_startup()
        
        schedule.every().hour.do(self.send_status)
        self.run_scan()
        schedule.every(CONFIG['scan_interval_minutes']).minutes.do(self.run_scan)
        
        logging.info(f"⏰ Running (scan every {CONFIG['scan_interval_minutes']} min)...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"❌ Error: {e}")
                time.sleep(5)

def main():
    print("\n" + "=" * 60)
    print("🤖 CRYPTO TRADING BOT")
    print("=" * 60 + "\n")
    
    if not validate_config():
        sys.exit(1)
    
    bot = BinanceScanner(CONFIG)
    bot.run()

if __name__ == "__main__":
    main()
