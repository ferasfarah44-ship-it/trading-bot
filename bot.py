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

# Configuration
CONFIG = {
    'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
    'ma_fast': 7,
    'ma_medium': 25,
    'ma_slow': 99,
    'ma_long': 200,
    'min_volume_ratio': 1.0,  # خفضت من 1.3 إلى 1.0
    'max_rsi': 85,  # زدت من 75 إلى 85
    'min_rsi': 30,
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
        msg = "🔊 <b>ADVANCED MA7/MA25 BOT</b>\n\n✅ Connected!"
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
        # MAs
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
        
        # MA slopes
        df['MA7_slope'] = df['MA7'].pct_change(3) * 100
        df['MA25_slope'] = df['MA25'].pct_change(3) * 100
        
        return df
    
    def check_all_signals(self, df):
        """
        Check MULTIPLE signal types:
        1. Fresh crossover
        2. Already trending
        3. Strong momentum breakout
        4. Volume spike
        """
        if len(df) < 30:
            return {'signal': False}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # === SIGNAL TYPE 1: Fresh MA7/MA25 Crossover ===
        fresh_cross = (previous['MA7'] <= previous['MA25'] and 
                      current['MA7'] > current['MA25'])
        
        # === SIGNAL TYPE 2: Already Trending (MA7 above MA25) ===
        ma7_above_ma25 = current['MA7'] > current['MA25']
        ma7_trending = current['MA7'] > previous['MA7']
        ma25_trending = current['MA25'] > previous['MA25']
        price_above_mas = current['close'] > max(current['MA7'], current['MA25'])
        
        # Distance between MAs
        ma_distance = ((current['MA7'] - current['MA25']) / current['MA25']) * 100
        
        # === SIGNAL TYPE 3: Strong Momentum ===
        strong_momentum = (current['change_24h'] > 10 and  # +10% in 24h
                          current['momentum'] > 5 and
                          current['MA7_slope'] > 0)
        
        # === SIGNAL TYPE 4: Volume Spike ===
        volume_ratio = current['volume'] / current['volume_MA'] if current['volume_MA'] > 0 else 0
        volume_spike = volume_ratio > self.config['min_volume_ratio']
        
        # === RSI Check (More Flexible) ===
        rsi_ok = self.config['min_rsi'] < current['RSI'] < self.config['max_rsi']
        
        # === Price above MA200 (Long term trend) ===
        above_ma200 = current['close'] > current['MA200']
        
        # === Combine all signals ===
        
        # Type 1: Fresh crossover with volume
        signal_1 = fresh_cross and volume_spike and rsi_ok
        
        # Type 2: Already trending (MA7 > MA25, both up, price above)
        signal_2 = (ma7_above_ma25 and ma7_trending and ma25_trending and 
                   price_above_mas and volume_ratio > 1.0 and rsi_ok and 
                   ma_distance < 15)  # Not too extended
        
        # Type 3: Strong momentum breakout (like DCR)
        signal_3 = (strong_momentum and ma7_above_ma25 and 
                   volume_spike and above_ma200)
        
        # Any signal triggers
        signal = signal_1 or signal_2 or signal_3
        
        # Determine signal type
        if signal_1:
            signal_type = "🟢 FRESH CROSSOVER"
        elif signal_2:
            signal_type = "📈 TRENDING"
        elif signal_3:
            signal_type = "🚀 MOMENTUM BREAKOUT"
        else:
            signal_type = "NONE"
        
        return {
            'signal': signal,
            'signal_type': signal_type,
            'fresh_cross': fresh_cross,
            'ma7_above_ma25': ma7_above_ma25,
            'ma7_trending': ma7_trending,
            'ma25_trending': ma25_trending,
            'price_above_mas': price_above_mas,
            'ma_distance': ma_distance,
            'strong_momentum': strong_momentum,
            'volume_ratio': volume_ratio,
            'volume_spike': volume_spike,
            'rsi_ok': rsi_ok,
            'above_ma200': above_ma200,
            'current_price': current['close'],
            'ma7': current['MA7'],
            'ma25': current['MA25'],
            'ma99': current['MA99'],
            'ma200': current['MA200'],
            'rsi': current['RSI'],
            'atr': current['ATR'],
            'change_1h': current['change_1h'],
            'change_4h': current['change_4h'],
            'change_24h': current['change_24h'],
            'momentum': current['momentum'],
            'ma7_slope': current['MA7_slope']
        }
    
    def calculate_dynamic_targets(self, df, entry_price):
        current = df.iloc[-1]
        
        # ATR-based
        atr = current['ATR']
        atr_percent = (atr / entry_price) * 100
        
        # Adjust based on momentum
        momentum_factor = 1.0
        if current['change_24h'] > 15:
            momentum_factor = 1.8  # High momentum - bigger targets
        elif current['change_24h'] > 10:
            momentum_factor = 1.5
        elif current['change_24h'] > 5:
            momentum_factor = 1.2
        
        if atr_percent > 5:
            tp1_percent = max(3, atr_percent * 0.7) * momentum_factor
            tp2_percent = max(6, atr_percent * 1.3) * momentum_factor
            tp3_percent = max(10, atr_percent * 2.0) * momentum_factor
        else:
            tp1_percent = max(2.5, atr_percent) * momentum_factor
            tp2_percent = max(5, atr_percent * 1.8) * momentum_factor
            tp3_percent = max(8, atr_percent * 2.5) * momentum_factor
        
        # Stop loss
        sl_percent = max(2, atr_percent * 1.2)
        
        return {
            'entry': entry_price,
            'tp1': entry_price * (1 + tp1_percent/100),
            'tp1_percent': round(tp1_percent, 2),
            'tp2': entry_price * (1 + tp2_percent/100),
            'tp2_percent': round(tp2_percent, 2),
            'tp3': entry_price * (1 + tp3_percent/100),
            'tp3_percent': round(tp3_percent, 2),
            'sl': entry_price * (1 - sl_percent/100),
            'sl_percent': round(sl_percent, 2)
        }
    
    def format_message(self, symbol, data, targets):
        # Price changes
        change_1h = data['change_1h']
        change_4h = data['change_4h']
        change_24h = data['change_24h']
        
        return f"""
{data['signal_type']}
━━━━━━━━━━━━━━━━━━━━━━

<b>Pair:</b> {symbol}
💰 <b>Price:</b> ${data['current_price']:.6f}

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>PRICE ACTION:</b>
━━━━━━━━━━━━━━━━━━━━━━

├ 1h: {change_1h:+.2f}%
├ 4h: {change_4h:+.2f}%
└ 24h: {change_24h:+.2f}%

━━━━━━━━━━━━━━━━━━━━━━
🟡 <b>MA7/MA25:</b>
━━━━━━━━━━━━━━━━━━━━━━

🟡 MA7: ${data['ma7']:.4f}
🟣 MA25: ${data['ma25']:.4f}
📏 Distance: {data['ma_distance']:+.2f}%

├ MA7 Slope: {data['ma7_slope']:+.2f}%
└ Position: {'✅ Above' if data['price_above_mas'] else '❌ Below'}

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>INDICATORS:</b>
━━━━━━━━━━━━━━━━━━━━━━

├ RSI: {data['rsi']:.2f} {'✅' if data['rsi_ok'] else '⚠️'}
├ Volume: {data['volume_ratio']:.2f}x
├ Momentum: {data['momentum']:+.2f}%
└ Above MA200: {'✅' if data['above_ma200'] else '❌'}

━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>TARGETS:</b>
━━━━━━━━━━━━━━━━━━━━━━

🟢 Entry: ${data['current_price']:.6f}

🎯 TP1: ${targets['tp1']:.6f} (+{targets['tp1_percent']}%)
🎯 TP2: ${targets['tp2']:.6f} (+{targets['tp2_percent']}%)
🎯 TP3: ${targets['tp3']:.6f} (+{targets['tp3_percent']}%)

🔴 SL: ${targets['sl']:.6f} (-{targets['sl_percent']}%)

📊 R:R: {targets['tp1_percent']/targets['sl_percent']:.2f}

━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    def run_scan(self):
        pairs = self.get_usdt_pairs()
        if not pairs:
            return 0
        
        logging.info(f"🔍 Advanced scan ({len(pairs)} pairs)...")
        found = 0
        
        for symbol in pairs:
            try:
                df = self.get_ohlcv_data(symbol)
                if df is None:
                    continue
                
                df = self.calculate_indicators(df)
                data = self.check_all_signals(df)
                
                if data['signal']:
                    targets = self.calculate_dynamic_targets(df, data['current_price'])
                    msg = self.format_message(symbol, data, targets)
                    
                    if self.telegram.send_message(msg):
                        found += 1
                        self.signals_count += 1
                        logging.info(f"🚀 {symbol} | {data['signal_type']} | 24h: {data['change_24h']:+.2f}%")
                
                self.analyzed_pairs.add(symbol)
                
            except Exception as e:
                logging.error(f"❌ Error {symbol}: {e}")
                continue
        
        logging.info(f"✅ Done. Found {found} signals")
        return found
    
    def send_startup(self):
        msg = f"""
🤖 <b>ADVANCED MA7/MA25 BOT</b>

✅ 3 Signal Types:
🟢 Fresh Crossover
📈 Trending
🚀 Momentum Breakout

📊 200 pairs | Every {CONFIG['scan_interval_minutes']} min

⏰ {datetime.now().strftime('%H:%M:%S')}
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
        logging.info("🚀 Starting Advanced Bot...")
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
    print("🤖 ADVANCED MA7/MA25 BOT")
    print("=" * 60 + "\n")
    
    if not validate_config():
        sys.exit(1)
    
    bot = BinanceScanner(CONFIG)
    bot.run()

if __name__ == "__main__":
    main()
