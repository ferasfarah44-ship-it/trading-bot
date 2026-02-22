import ccxt
import pandas as pd
import numpy as np
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

# Setup logging - MORE DETAILED
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more details
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def validate_config():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or token == 'None':
        print("❌ TELEGRAM_BOT_TOKEN missing!")
        return False
    
    if not chat_id or chat_id == 'None':
        print("❌ TELEGRAM_CHAT_ID missing!")
        return False
    
    print("✅ Configuration valid!")
    return True

# Configuration - MORE FLEXIBLE
CONFIG = {
    'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
    'ma_fast': 7,
    'ma_medium': 25,
    'ma_slow': 99,
    'ma_long': 200,
    'min_volume_ratio': 0.8,  # خفضت أكثر - من 1.0 إلى 0.8
    'max_rsi': 90,  # وسعت أكثر - من 85 إلى 90
    'min_rsi': 25,  # وسعت من 30 إلى 25
    'min_price_change_24h': 5,  # خفضت من 10 إلى 5
    'max_ma_distance': 20,  # زدت من 15 إلى 20
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
            return True
        except Exception as e:
            logging.error(f"❌ Telegram error: {e}")
            return False
    
    def test_connection(self):
        msg = "🔊 <b>BOT STARTED</b>\n\n✅ Advanced Detection Enabled!"
        return self.send_message(msg)

class BinanceScanner:
    def __init__(self, config):
        self.config = config
        self.exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
        self.telegram = TelegramNotifier(config['telegram_bot_token'], config['telegram_chat_id'])
        self.start_time = None
        self.signals_count = 0
        self.analyzed_pairs = set()
        self.debug_count = 0
    
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
        df['MA7'] = df['close'].rolling(window=self.config['ma_fast']).mean()
        df['MA25'] = df['close'].rolling(window=self.config['ma_medium']).mean()
        df['MA99'] = df['close'].rolling(window=self.config['ma_slow']).mean()
        df['MA200'] = df['close'].rolling(window=self.config['ma_long']).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))
        
        # Volume
        df['volume_MA'] = df['volume'].rolling(window=20).mean()
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['tr'].rolling(window=14).mean()
        
        # Price changes
        df['change_1h'] = df['close'].pct_change(1) * 100
        df['change_4h'] = df['close'].pct_change(4) * 100
        df['change_24h'] = df['close'].pct_change(24) * 100
        
        # Momentum
        df['momentum'] = df['close'].pct_change(14) * 100
        df['MA7_slope'] = df['MA7'].pct_change(3) * 100
        
        return df
    
    def check_signals_with_debug(self, symbol, df):
        """
        Check signals WITH DETAILED DEBUGGING
        Shows WHY a pair passes or fails
        """
        if len(df) < 30:
            return {'signal': False, 'reason': 'Not enough data'}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Calculate all conditions
        conditions = {}
        
        # Basic MA conditions
        conditions['ma7_above_ma25'] = current['MA7'] > current['MA25']
        conditions['fresh_cross'] = (previous['MA7'] <= previous['MA25'] and 
                                    current['MA7'] > current['MA25'])
        conditions['ma7_trending'] = current['MA7'] > previous['MA7']
        conditions['ma25_trending'] = current['MA25'] > previous['MA25']
        conditions['price_above_mas'] = current['close'] > max(current['MA7'], current['MA25'])
        conditions['above_ma200'] = current['close'] > current['MA200']
        
        # MA distance
        ma_distance = ((current['MA7'] - current['MA25']) / current['MA25']) * 100
        conditions['ma_distance_ok'] = abs(ma_distance) < self.config['max_ma_distance']
        conditions['ma_distance'] = ma_distance
        
        # Volume
        volume_ratio = current['volume'] / current['volume_MA'] if current['volume_MA'] > 0 else 0
        conditions['volume_ratio'] = volume_ratio
        conditions['volume_ok'] = volume_ratio > self.config['min_volume_ratio']
        
        # RSI
        conditions['rsi'] = current['RSI']
        conditions['rsi_ok'] = self.config['min_rsi'] < current['RSI'] < self.config['max_rsi']
        
        # Price changes
        conditions['change_24h'] = current['change_24h'] if not pd.isna(current['change_24h']) else 0
        conditions['momentum_ok'] = conditions['change_24h'] > self.config['min_price_change_24h']
        conditions['ma7_slope'] = current['MA7_slope'] if not pd.isna(current['MA7_slope']) else 0
        
        # === SIGNAL TYPES ===
        
        # Type 1: Fresh crossover
        conditions['signal_1'] = (conditions['fresh_cross'] and 
                                 conditions['volume_ok'] and 
                                 conditions['rsi_ok'])
        
        # Type 2: Trending
        conditions['signal_2'] = (conditions['ma7_above_ma25'] and 
                                 conditions['ma7_trending'] and 
                                 conditions['ma25_trending'] and 
                                 conditions['price_above_mas'] and 
                                 conditions['ma_distance_ok'] and 
                                 conditions['rsi_ok'])
        
        # Type 3: Momentum breakout
        conditions['signal_3'] = (conditions['momentum_ok'] and 
                                 conditions['ma7_above_ma25'] and 
                                 conditions['volume_ok'] and 
                                 conditions['above_ma200'])
        
        # Any signal
        conditions['signal'] = conditions['signal_1'] or conditions['signal_2'] or conditions['signal_3']
        
        # Determine signal type
        if conditions['signal_1']:
            conditions['signal_type'] = "🟢 FRESH CROSSOVER"
        elif conditions['signal_2']:
            conditions['signal_type'] = "📈 TRENDING"
        elif conditions['signal_3']:
            conditions['signal_type'] = "🚀 MOMENTUM"
        else:
            conditions['signal_type'] = "NONE"
        
        # Add current values
        conditions['current_price'] = current['close']
        conditions['ma7'] = current['MA7']
        conditions['ma25'] = current['MA25']
        conditions['ma99'] = current['MA99']
        conditions['ma200'] = current['MA200']
        conditions['atr'] = current['ATR']
        
        # Debug logging every 50 pairs or when signal found
        self.debug_count += 1
        if conditions['signal'] or self.debug_count % 50 == 0:
            logging.info(f"\n🔍 DEBUG: {symbol}")
            logging.info(f"  MA7>MA25: {conditions['ma7_above_ma25']}")
            logging.info(f"  Fresh Cross: {conditions['fresh_cross']}")
            logging.info(f"  Volume: {volume_ratio:.2f}x ({'✅' if conditions['volume_ok'] else '❌'})")
            logging.info(f"  RSI: {current['RSI']:.1f} ({'✅' if conditions['rsi_ok'] else '❌'})")
            logging.info(f"  24h Change: {conditions['change_24h']:+.2f}%")
            logging.info(f"  Signal: {conditions['signal_type']}")
            logging.info("-" * 50)
        
        return conditions
    
    def calculate_targets(self, entry_price, data):
        atr = data['atr']
        atr_percent = (atr / entry_price) * 100 if entry_price > 0 else 3
        
        # Adjust based on momentum
        momentum_factor = 1.0
        if data['change_24h'] > 15:
            momentum_factor = 1.8
        elif data['change_24h'] > 10:
            momentum_factor = 1.5
        elif data['change_24h'] > 5:
            momentum_factor = 1.3
        
        tp1_pct = max(2, atr_percent * 0.8) * momentum_factor
        tp2_pct = max(4, atr_percent * 1.5) * momentum_factor
        tp3_pct = max(8, atr_percent * 2.5) * momentum_factor
        sl_pct = max(1.5, atr_percent * 1.2)
        
        return {
            'entry': entry_price,
            'tp1': entry_price * (1 + tp1_pct/100),
            'tp1_percent': round(tp1_pct, 2),
            'tp2': entry_price * (1 + tp2_pct/100),
            'tp2_percent': round(tp2_pct, 2),
            'tp3': entry_price * (1 + tp3_pct/100),
            'tp3_percent': round(tp3_pct, 2),
            'sl': entry_price * (1 - sl_pct/100),
            'sl_percent': round(sl_pct, 2)
        }
    
    def format_message(self, symbol, data, targets):
        return f"""
{data['signal_type']}
━━━━━━━━━━━━━━━━━━━━

<b>{symbol}</b>
💰 ${data['current_price']:.6f}

📊 <b>Indicators:</b>
├ MA7: ${data['ma7']:.4f}
├ MA25: ${data['ma25']:.4f}
├ RSI: {data['rsi']:.1f}
├ Vol: {data['volume_ratio']:.2f}x
└ 24h: {data['change_24h']:+.2f}%

🎯 <b>Targets:</b>
├ TP1: +{targets['tp1_percent']}%
├ TP2: +{targets['tp2_percent']}%
├ TP3: +{targets['tp3_percent']}%
└ SL: -{targets['sl_percent']}%

⏰ {datetime.now().strftime('%H:%M')}
"""
    
    def run_scan(self):
        pairs = self.get_usdt_pairs()
        if not pairs:
            return 0
        
        logging.info(f"\n🔍 Starting scan of {len(pairs)} pairs...")
        found = 0
        passed_filters = 0
        
        for symbol in pairs:
            try:
                df = self.get_ohlcv_data(symbol)
                if df is None:
                    continue
                
                df = self.calculate_indicators(df)
                data = self.check_signals_with_debug(symbol, df)
                
                if data['signal']:
                    targets = self.calculate_targets(data['current_price'], data)
                    msg = self.format_message(symbol, data, targets)
                    
                    if self.telegram.send_message(msg):
                        found += 1
                        self.signals_count += 1
                        logging.info(f"✅ SIGNAL FOUND: {symbol} - {data['signal_type']}")
                
                # Count how many pass basic filters
                if data.get('ma7_above_ma25', False) and data.get('rsi_ok', False):
                    passed_filters += 1
                
                self.analyzed_pairs.add(symbol)
                
            except Exception as e:
                logging.error(f"❌ Error {symbol}: {e}")
                continue
        
        logging.info(f"\n✅ Scan Complete:")
        logging.info(f"  Total pairs: {len(pairs)}")
        logging.info(f"  Passed filters: {passed_filters}")
        logging.info(f"  Signals found: {found}")
        logging.info("=" * 50)
        
        return found
    
    def send_status(self):
        uptime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        msg = f"""
⏰ <b>STATUS</b>

✅ Running
⏳ {str(uptime).split('.')[0]}
📊 {len(self.analyzed_pairs)} scanned
📈 {self.signals_count} signals
"""
        return self.telegram.send_message(msg)
    
    def run(self):
        logging.info("🚀 Starting Advanced Bot...")
        self.start_time = datetime.now()
        
        if not self.telegram.test_connection():
            logging.error("❌ Telegram test failed!")
            return
        
        logging.info("✅ Bot started successfully!")
        logging.info(f"Configuration:")
        logging.info(f"  Min Volume Ratio: {self.config['min_volume_ratio']}")
        logging.info(f"  RSI Range: {self.config['min_rsi']}-{self.config['max_rsi']}")
        logging.info(f"  Min 24h Change: {self.config['min_price_change_24h']}%")
        logging.info(f"  Max MA Distance: {self.config['max_ma_distance']}%")
        
        schedule.every().hour.do(self.send_status)
        self.run_scan()
        schedule.every(self.config['scan_interval_minutes']).minutes.do(self.run_scan)
        
        logging.info(f"⏰ Bot running (scan every {self.config['scan_interval_minutes']} min)...")
        
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
    print("🤖 ADVANCED BOT - RELAXED CONDITIONS")
    print("=" * 60 + "\n")
    
    if not validate_config():
        sys.exit(1)
    
    bot = BinanceScanner(CONFIG)
    bot.run()

if __name__ == "__main__":
    main()
