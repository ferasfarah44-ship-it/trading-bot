import ccxt
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import schedule
import os
from dotenv import load_dotenv
import sys

# Load environment variables
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

def validate_telegram_token():
    """Validate Telegram token before anything else"""
    print("=" * 70)
    print("🔍 VALIDATING TELEGRAM CREDENTIALS")
    print("=" * 70)
    
    token = os.getenv('8303823776:AAGW3VhBU3Mo3GPiCzpQqaKIkzlE4mi664w)
    chat_id = os.getenv('7960335113)
    
    print(f"\n📱 TELEGRAM_BOT_TOKEN:")
    print(f"   Type: {type(token)}")
    print(f"   Value: '{token}'")
    print(f"   Is None: {token is None}")
    print(f"   Is 'None' string: {token == 'None'}")
    
    print(f"\n👤 TELEGRAM_CHAT_ID:")
    print(f"   Type: {type(chat_id)}")
    print(f"   Value: '{chat_id}'")
    print(f"   Is None: {chat_id is None}")
    
    # Check for common mistakes
    if token is None:
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN is None!")
        print("   → Variable not set in Railway")
        return False
    
    if token == 'None':
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN is the string 'None'!")
        print("   → You added the word 'None' instead of actual token")
        print("   → Get real token from @BotFather on Telegram")
        return False
    
    if token == 'your_telegram_bot_token_here':
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN is default value!")
        print("   → Replace with your actual bot token")
        return False
    
    if not token or len(token) < 40:
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN is too short!")
        print("   → Token should be like: 1234567890:ABCdef...")
        return False
    
    if chat_id is None:
        print("\n❌ ERROR: TELEGRAM_CHAT_ID is None!")
        return False
    
    print("\n✅ Credentials look good!")
    print("=" * 70)
    return True

# Configuration
CONFIG = {
    'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
    'ma_periods': {
        'fast': 7,
        'medium': 25,
        'slow': 99,
        'long': 200
    },
    'targets': {
        'tp1_percent': 3,
        'tp2_percent': 6,
        'tp3_percent': 10,
        'stop_loss': 2
    },
    'min_volume_24h': 1000000,
    'scan_interval_minutes': 5
}

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            logging.info("✅ Telegram message sent successfully")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def test_connection(self) -> bool:
        message = "🔊 <b>BOT CONNECTION TEST</b>\n\n✅ Bot is connected!\n🕐 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return self.send_message(message)

class BinanceScanner:
    def __init__(self, config: Dict):
        self.config = config
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.telegram = TelegramNotifier(
            config['telegram_bot_token'],
            config['telegram_chat_id']
        )
        self.analyzed_pairs = set()
        self.start_time = None
        self.signals_count = 0
    
    def get_usdt_pairs(self) -> List[str]:
        try:
            markets = self.exchange.load_markets()
            usdt_pairs = [
                symbol for symbol in markets.keys() 
                if symbol.endswith('/USDT') and not symbol.startswith('1000')
            ]
            usdt_pairs.sort()
            logging.info(f"✅ Found {len(usdt_pairs)} USDT pairs")
            return usdt_pairs[:200]
        except Exception as e:
            logging.error(f"❌ Error fetching USDT pairs: {e}")
            return []
    
    def get_ohlcv_data(self, symbol: str, timeframe: str = '1h', limit: int = 300) -> Optional[pd.DataFrame]:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logging.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['MA7'] = df['close'].rolling(window=self.config['ma_periods']['fast']).mean()
        df['MA25'] = df['close'].rolling(window=self.config['ma_periods']['medium']).mean()
        df['MA99'] = df['close'].rolling(window=self.config['ma_periods']['slow']).mean()
        df['MA200'] = df['close'].rolling(window=self.config['ma_periods']['long']).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['volume_MA'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def check_buy_signal(self, df: pd.DataFrame) -> Dict:
        if len(df) < 200:
            return {'signal': False}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        ma7_crossed_up = (previous['MA7'] <= previous['MA25'] and current['MA7'] > current['MA25'])
        price_above_ma7 = current['close'] > current['MA7']
        ma7_trending_up = current['MA7'] > previous['MA7']
        volume_spike = current['volume'] > (current['volume_MA'] * 1.5)
        rsi_ok = 30 < current['RSI'] < 70
        price_change_24h = ((current['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close']) * 100 if len(df) >= 24 else 0
        
        signal = (ma7_crossed_up or (price_above_ma7 and ma7_trending_up)) and volume_spike and rsi_ok
        
        return {
            'signal': signal,
            'ma7_crossed_up': ma7_crossed_up,
            'price_above_ma7': price_above_ma7,
            'ma7_trending_up': ma7_trending_up,
            'volume_spike': volume_spike,
            'rsi': current['RSI'],
            'price_change_24h': price_change_24h,
            'current_price': current['close'],
            'ma7': current['MA7'],
            'ma25': current['MA25'],
            'ma99': current['MA99'],
            'ma200': current['MA200'],
            'volume': current['volume']
        }
    
    def calculate_targets(self, entry_price: float) -> Dict:
        tp1 = entry_price * (1 + self.config['targets']['tp1_percent'] / 100)
        tp2 = entry_price * (1 + self.config['targets']['tp2_percent'] / 100)
        tp3 = entry_price * (1 + self.config['targets']['tp3_percent'] / 100)
        sl = entry_price * (1 - self.config['targets']['stop_loss'] / 100)
        
        return {
            'entry': entry_price,
            'tp1': tp1,
            'tp1_percent': f"+{self.config['targets']['tp1_percent']}%",
            'tp2': tp2,
            'tp2_percent': f"+{self.config['targets']['tp2_percent']}%",
            'tp3': tp3,
            'tp3_percent': f"+{self.config['targets']['tp3_percent']}%",
            'stop_loss': sl,
            'stop_loss_percent': f"-{self.config['targets']['stop_loss']}%"
        }
    
    def format_signal_message(self, symbol: str, signal_data: Dict, targets: Dict) -> str:
        return f"""
🚀 <b>NEW TRADING SIGNAL!</b> 🚀

<b>Pair:</b> {symbol}
💰 <b>Price:</b> ${signal_data['current_price']:.6f}

📈 <b>Analysis:</b>
├ MA7: ${signal_data['ma7']:.6f}
├ MA25: ${signal_data['ma25']:.6f}
├ RSI: {signal_data['rsi']:.2f}
└ 24h: {signal_data['price_change_24h']:+.2f}%

🎯 <b>Targets:</b>
├ Entry: ${targets['entry']:.6f}
├ TP1: ${targets['tp1']:.6f} (+3%)
├ TP2: ${targets['tp2']:.6f} (+6%)
├ TP3: ${targets['tp3']:.6f} (+10%)
└ SL: ${targets['stop_loss']:.6f} (-2%)

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def analyze_pair(self, symbol: str) -> Optional[Dict]:
        try:
            df = self.get_ohlcv_data(symbol, timeframe='1h', limit=300)
            if df is None or len(df) < 200:
                return None
            
            df = self.calculate_indicators(df)
            signal_data = self.check_buy_signal(df)
            
            if signal_data['signal']:
                targets = self.calculate_targets(signal_data['current_price'])
                return {'symbol': symbol, 'signal_data': signal_data, 'targets': targets}
            
            return None
        except Exception as e:
            logging.error(f"❌ Error analyzing {symbol}: {e}")
            return None
    
    def send_startup_message(self):
        message = f"""
🤖 <b>BOT STARTED</b> 🤖

✅ Bot is running
📊 Monitoring: 200 USDT pairs
📈 Strategy: MA7 Crossover
⏱️ Scan: Every {CONFIG['scan_interval_minutes']} min

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.telegram.send_message(message)
    
    def send_hourly_status(self):
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        message = f"""
⏰ <b>HOURLY STATUS</b>

✅ Bot running
⏳ Uptime: {str(uptime).split('.')[0]}
📊 Pairs: {len(self.analyzed_pairs)}
📈 Signals: {self.signals_count}
"""
        return self.telegram.send_message(message)
    
    def run_scan(self):
        pairs = self.get_usdt_pairs()
        if not pairs:
            return 0
        
        logging.info(f"🔍 Scanning {len(pairs)} pairs...")
        signals_found = 0
        
        for i, symbol in enumerate(pairs, 1):
            try:
                time.sleep(0.1)
                result = self.analyze_pair(symbol)
                
                if result:
                    message = self.format_signal_message(
                        result['symbol'],
                        result['signal_data'],
                        result['targets']
                    )
                    if self.telegram.send_message(message):
                        signals_found += 1
                        self.signals_count += 1
                        logging.info(f"🚀 Signal: {symbol}")
                
                self.analyzed_pairs.add(symbol)
                
                if i % 50 == 0:
                    logging.info(f"📊 Progress: {i}/{len(pairs)}")
                    
            except Exception as e:
                logging.error(f"❌ Error {symbol}: {e}")
                continue
        
        logging.info(f"✅ Done. Found {signals_found} signals.")
        return signals_found
    
    def run(self):
        logging.info("🚀 Starting Bot...")
        self.start_time = datetime.now()
        
        logging.info("📱 Testing Telegram...")
        if not self.telegram.test_connection():
            logging.error("❌ Telegram test FAILED!")
            return
        
        logging.info("✅ Telegram OK!")
        self.send_startup_message()
        
        schedule.every().hour.do(self.send_hourly_status)
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
    print("\n" + "=" * 70)
    print("🤖 CRYPTO TRADING BOT - MA7 STRATEGY")
    print("=" * 70 + "\n")
    
    if not validate_telegram_token():
        print("\n❌ VALIDATION FAILED - Fix errors and redeploy\n")
        sys.exit(1)
    
    print("✅ Validation passed\n")
    
    try:
        bot = BinanceScanner(CONFIG)
        bot.run()
    except Exception as e:
        logging.error(f"❌ Fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
