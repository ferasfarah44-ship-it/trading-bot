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

# Configuration - NO Binance API Keys Needed!
CONFIG = {
    'telegram_bot_token': os.getenv('8452767198:AAFeyAUHaI6X09Jns6Q8Lnpp3edOOIMLLsE'),
    'telegram_chat_id': os.getenv('7960335113'),
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class TelegramNotifier:
    """Send notifications via Telegram"""
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "HTML"):
        """Send message to Telegram"""
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
        """Test Telegram connection"""
        message = "🔊 <b>BOT CONNECTION TEST</b>\n\n✅ Bot is connected and working!\n🕐 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return self.send_message(message)

class BinanceScanner:
    """Scan Binance for USDT pairs and analyze MA crossovers"""
    def __init__(self, config: Dict):
        self.config = config
        # NO API KEYS NEEDED - Public data only!
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
        """Get all USDT trading pairs from Binance"""
        try:
            logging.info("📊 Fetching USDT pairs from Binance...")
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
        """Fetch OHLCV data for a symbol"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logging.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Moving Averages and other indicators"""
        df['MA7'] = df['close'].rolling(window=self.config['ma_periods']['fast']).mean()
        df['MA25'] = df['close'].rolling(window=self.config['ma_periods']['medium']).mean()
        df['MA99'] = df['close'].rolling(window=self.config['ma_periods']['slow']).mean()
        df['MA200'] = df['close'].rolling(window=self.config['ma_periods']['long']).mean()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Calculate volume MA
        df['volume_MA'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def check_buy_signal(self, df: pd.DataFrame) -> Dict:
        """Check for buy signal based on MA7 (yellow line) crossover"""
        if len(df) < 200:
            return {'signal': False}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Check if MA7 crossed above MA25
        ma7_crossed_up = (previous['MA7'] <= previous['MA25'] and 
                          current['MA7'] > current['MA25'])
        
        # Check if price is above MA7
        price_above_ma7 = current['close'] > current['MA7']
        
        # Check if MA7 is trending up
        ma7_trending_up = current['MA7'] > previous['MA7']
        
        # Check volume spike
        volume_spike = current['volume'] > (current['volume_MA'] * 1.5)
        
        # Check RSI (not overbought)
        rsi_ok = 30 < current['RSI'] < 70
        
        # Calculate price change in last 24h
        price_change_24h = ((current['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close']) * 100 if len(df) >= 24 else 0
        
        # Generate signal
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
        """Calculate take profit targets and stop loss"""
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
        """Format the signal message for Telegram"""
        message = f"""
🚀 <b>NEW TRADING SIGNAL DETECTED!</b> 🚀

<b>Pair:</b> {symbol}
💰 <b>Current Price:</b> ${signal_data['current_price']:.6f}

📈 <b>Technical Analysis:</b>
├ MA7 (Yellow): ${signal_data['ma7']:.6f}
├ MA25: ${signal_data['ma25']:.6f}
├ MA99: ${signal_data['ma99']:.6f}
├ MA200: ${signal_data['ma200']:.6f}
├ RSI: {signal_data['rsi']:.2f}
└ 24h Change: {signal_data['price_change_24h']:+.2f}%

🎯 <b>Entry & Targets:</b>
├  Entry: ${targets['entry']:.6f}
├ 🎯 TP1: ${targets['tp1']:.6f} ({targets['tp1_percent']})
├ 🎯 TP2: ${targets['tp2']:.6f} ({targets['tp2_percent']})
├ 🎯 TP3: ${targets['tp3']:.6f} ({targets['tp3_percent']})
└ 🔴 Stop Loss: ${targets['stop_loss']:.6f} ({targets['stop_loss_percent']})

📊 <b>Signal Conditions:</b>
{'✅' if signal_data['ma7_crossed_up'] else '❌'} MA7 Crossed Up
{'✅' if signal_data['price_above_ma7'] else '❌'} Price Above MA7
{'✅' if signal_data['ma7_trending_up'] else '❌'} MA7 Trending Up
{'✅' if signal_data['volume_spike'] else '❌'} Volume Spike
{'✅' if 30 < signal_data['rsi'] < 70 else '❌'} RSI OK

⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message
    
    def analyze_pair(self, symbol: str) -> Optional[Dict]:
        """Analyze a single trading pair"""
        try:
            df = self.get_ohlcv_data(symbol, timeframe='1h', limit=300)
            if df is None or len(df) < 200:
                return None
            
            df = self.calculate_indicators(df)
            signal_data = self.check_buy_signal(df)
            
            if signal_data['signal']:
                targets = self.calculate_targets(signal_data['current_price'])
                return {
                    'symbol': symbol,
                    'signal_data': signal_data,
                    'targets': targets
                }
            
            return None
        except Exception as e:
            logging.error(f"❌ Error analyzing {symbol}: {e}")
            return None
    
    def send_startup_message(self):
        """Send confirmation message when bot starts"""
        message = f"""
🤖 <b>TRADING BOT STARTED</b> 🤖

✅ Bot is now running and scanning the market
📊 Monitoring: 200 USDT pairs
📈 Strategy: MA7 (Yellow Line) Crossover
⏱️ Analysis: Continuous (every {CONFIG['scan_interval_minutes']} minutes)
📢 Status updates: Every hour

<b>Configuration:</b>
├ MA Periods: 7, 25, 99, 200
├ Take Profit Levels: 3%, 6%, 10%
└ Stop Loss: 2%

⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>The bot will send alerts when buy conditions are met!</i>
"""
        success = self.telegram.send_message(message)
        if success:
            logging.info("✅ Startup message sent to Telegram")
        else:
            logging.error("❌ Failed to send startup message")
        return success
    
    def send_hourly_status(self):
        """Send hourly status update"""
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        message = f"""
⏰ <b>HOURLY STATUS UPDATE</b> ⏰

✅ Bot is running normally
🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏳ Uptime: {str(uptime).split('.')[0]}
📊 Pairs Analyzed: {len(self.analyzed_pairs)}
🔍 Active Monitoring: 200 USDT pairs
📈 Total Signals Found: {self.signals_count}

<i>Bot is scanning for MA7 crossover signals...</i>
"""
        success = self.telegram.send_message(message)
        if success:
            logging.info("✅ Hourly status sent to Telegram")
        else:
            logging.error("❌ Failed to send hourly status")
        return success
    
    def run_scan(self):
        """Run a complete scan of all USDT pairs"""
        pairs = self.get_usdt_pairs()
        if not pairs:
            logging.warning("⚠️ No pairs to scan")
            return 0
        
        logging.info(f"🔍 Starting scan of {len(pairs)} pairs...")
        signals_found = 0
        
        for i, symbol in enumerate(pairs, 1):
            try:
                time.sleep(0.1)  # Rate limit
                result = self.analyze_pair(symbol)
                
                if result:
                    message = self.format_signal_message(
                        result['symbol'],
                        result['signal_data'],
                        result['targets']
                    )
                    success = self.telegram.send_message(message)
                    if success:
                        signals_found += 1
                        self.signals_count += 1
                        logging.info(f"🚀 Signal found and sent for {symbol}")
                    else:
                        logging.error(f"❌ Failed to send signal for {symbol}")
                
                self.analyzed_pairs.add(symbol)
                
                if i % 50 == 0:
                    logging.info(f"📊 Progress: {i}/{len(pairs)} pairs analyzed")
                    
            except Exception as e:
                logging.error(f"❌ Error processing {symbol}: {e}")
                continue
        
        logging.info(f"✅ Scan completed. Found {signals_found} signals.")
        return signals_found
    
    def run(self):
        """Main bot loop"""
        logging.info("🚀 Starting Trading Bot...")
        self.start_time = datetime.now()
        
        # Test Telegram connection first
        logging.info("📱 Testing Telegram connection...")
        if not self.telegram.test_connection():
            logging.error("❌ Telegram connection test failed!")
            logging.error("📝 Please check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return
        
        logging.info("✅ Telegram connection successful!")
        
        # Send startup message
        if not self.send_startup_message():
            logging.error("❌ Failed to send startup message")
            return
        
        # Schedule hourly status updates
        schedule.every().hour.do(self.send_hourly_status)
        
        # Initial scan
        logging.info("🔍 Running initial scan...")
        self.run_scan()
        
        # Schedule regular scans
        schedule.every(CONFIG['scan_interval_minutes']).minutes.do(self.run_scan)
        
        logging.info(f"⏰ Bot is now running continuously (scanning every {CONFIG['scan_interval_minutes']} minutes)...")
        
        # Main loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logging.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logging.error(f"❌ Error in main loop: {e}")
                time.sleep(5)

def validate_config():
    """Validate configuration"""
    print("=" * 60)
    print("🔍 Checking environment variables...")
    print("=" * 60)
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print(f"\n📱 TELEGRAM_BOT_TOKEN: {'✅ Found' if telegram_token else '❌ Missing'}")
    print(f"👤 TELEGRAM_CHAT_ID: {'✅ Found' if telegram_chat_id else '❌ Missing'}\n")
    
    if not telegram_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing!")
        print("\n📝 How to fix:")
        print("   1. Go to Railway Dashboard")
        print("   2. Click on your service")
        print("   3. Go to 'Variables' tab")
        print("   4. Add variable: TELEGRAM_BOT_TOKEN")
        print("   5. Value: your_bot_token_from_botfather\n")
        return False
    
    if not telegram_chat_id:
        print("❌ ERROR: TELEGRAM_CHAT_ID is missing!")
        print("\n📝 How to fix:")
        print("   1. Go to Railway Dashboard")
        print("   2. Click on your service")
        print("   3. Go to 'Variables' tab")
        print("   4. Add variable: TELEGRAM_CHAT_ID")
        print("   5. Value: your_chat_id (numbers)\n")
        return False
    
    print("✅ All environment variables found!")
    print("=" * 60)
    return True

def main():
    """Main function to run the bot"""
    print("\n" + "=" * 60)
    print("🤖 CRYPTO TRADING BOT - MA7 STRATEGY")
    print("=" * 60)
    print("🔓 NO API KEYS REQUIRED - Public Data Only!")
    print("=" * 60 + "\n")
    
    if not validate_config():
        print("\n❌ Configuration validation failed!")
        print("📝 Please add missing environment variables and redeploy.\n")
        sys.exit(1)
    
    print("✅ Configuration validated successfully")
    print("📊 Initializing bot...\n")
    
    try:
        bot = BinanceScanner(CONFIG)
        bot.run()
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
