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
    'ma_fast': 7,        # الخط الأصفر
    'ma_medium': 25,     # الخط الزهري الغامق
    'ma_slow': 99,
    'ma_long': 200,
    'min_volume_ratio': 1.3,  # Volume spike threshold
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
        msg = "🔊 <b>BOT TEST</b>\n\n✅ MA7/MA25 Crossover Bot Connected!"
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
        # MA7 (Yellow Line) - الخط الأصفر
        df['MA7'] = df['close'].rolling(window=self.config['ma_fast']).mean()
        
        # MA25 (Dark Pink Line) - الخط الزهري الغامق
        df['MA25'] = df['close'].rolling(window=self.config['ma_medium']).mean()
        
        # MA99 و MA200
        df['MA99'] = df['close'].rolling(window=self.config['ma_slow']).mean()
        df['MA200'] = df['close'].rolling(window=self.config['ma_long']).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))
        
        # Volume MA
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
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        return df
    
    def check_ma7_ma25_crossover(self, df):
        """
        Check for MA7/MA25 crossover
        MA7 = Yellow line (الخط الأصفر)
        MA25 = Dark Pink line (الخط الزهري الغامق)
        """
        if len(df) < 30:
            return {'signal': False}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        previous2 = df.iloc[-3]
        
        # 🟢 BULLISH CROSSOVER: MA7 crosses ABOVE MA25
        # الخط الأصفر يعبر فوق الزهري
        bullish_cross = (previous['MA7'] <= previous['MA25'] and 
                        current['MA7'] > current['MA25'])
        
        # 🔴 BEARISH CROSSOVER: MA7 crosses BELOW MA25
        # الخط الأصفر يعبر تحت الزهري
        bearish_cross = (previous['MA7'] >= previous['MA25'] and 
                        current['MA7'] < current['MA25'])
        
        # MA7 above MA25 (already crossed)
        ma7_above_ma25 = current['MA7'] > current['MA25']
        
        # Distance between MA7 and MA25
        ma_distance = ((current['MA7'] - current['MA25']) / current['MA25']) * 100
        
        # MA7 trending up
        ma7_trending_up = current['MA7'] > previous['MA7']
        
        # MA25 trending up
        ma25_trending_up = current['MA25'] > previous['MA25']
        
        # Price above both MAs
        price_above_mas = current['close'] > max(current['MA7'], current['MA25'])
        
        # Volume confirmation
        volume_ratio = current['volume'] / current['volume_MA'] if current['volume_MA'] > 0 else 0
        volume_ok = volume_ratio > self.config['min_volume_ratio']
        
        # RSI confirmation
        rsi_ok = 35 < current['RSI'] < 75
        
        # Strong bullish signal
        strong_bullish = (bullish_cross and volume_ok and rsi_ok and 
                         ma7_trending_up and price_above_mas)
        
        # Regular bullish signal
        regular_bullish = (ma7_above_ma25 and ma7_trending_up and 
                          price_above_mas and volume_ratio > 1.0 and rsi_ok)
        
        return {
            'signal': strong_bullish or regular_bullish,
            'type': 'BULLISH' if (bullish_cross or ma7_above_ma25) else 'BEARISH',
            'bullish_cross': bullish_cross,
            'bearish_cross': bearish_cross,
            'ma7_above_ma25': ma7_above_ma25,
            'ma_distance_percent': ma_distance,
            'ma7_trending_up': ma7_trending_up,
            'ma25_trending_up': ma25_trending_up,
            'price_above_mas': price_above_mas,
            'volume_ratio': volume_ratio,
            'volume_ok': volume_ok,
            'rsi_ok': rsi_ok,
            'current_price': current['close'],
            'ma7': current['MA7'],
            'ma25': current['MA25'],
            'ma99': current['MA99'],
            'ma200': current['MA200'],
            'rsi': current['RSI'],
            'atr': current['ATR'],
            'macd': current['MACD'],
            'macd_signal': current['MACD_signal']
        }
    
    def calculate_dynamic_targets(self, df, entry_price):
        """Calculate targets based on ATR and market conditions"""
        current = df.iloc[-1]
        
        # ATR-based calculation
        atr = current['ATR']
        atr_percent = (atr / entry_price) * 100
        
        # Adjust targets based on volatility
        if atr_percent > 5:
            tp1_percent = max(3, atr_percent * 0.7)
            tp2_percent = max(6, atr_percent * 1.3)
            tp3_percent = max(10, atr_percent * 2.0)
        else:
            tp1_percent = max(2.5, atr_percent)
            tp2_percent = max(5, atr_percent * 1.8)
            tp3_percent = max(8, atr_percent * 2.5)
        
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
            'sl_percent': round(sl_percent, 2),
            'atr': atr,
            'atr_percent': round(atr_percent, 2)
        }
    
    def format_message(self, symbol, data, targets):
        cross_type = "🟢 BULLISH CROSSOVER" if data['bullish_cross'] else "📈 TRENDING UP"
        
        return f"""
{cross_type}
━━━━━━━━━━━━━━━━━━━━

<b>Pair:</b> {symbol}
💰 <b>Price:</b> ${data['current_price']:.6f}

━━━━━━━━━━━━━━━━━━━━
📊 <b>MA7/MA25 ANALYSIS:</b>
━━━━━━━━━━━━━━━━━━━━

🟡 <b>MA7 (Yellow):</b> ${data['ma7']:.4f}
💗 <b>MA25 (Pink):</b> ${data['ma25']:.4f}
📏 <b>Distance:</b> {data['ma_distance_percent']:+.2f}%

├ MA7 Trend: {'⬆️ UP' if data['ma7_trending_up'] else '⬇️ DOWN'}
├ MA25 Trend: {'⬆️ UP' if data['ma25_trending_up'] else '⬇️ DOWN'}
└ Price Position: {'✅ Above Both' if data['price_above_mas'] else '❌ Below'}

━━━━━━━━━━━━━━━━━━━━
📈 <b>CONFIRMATION:</b>
━━━━━━━━━━━━━━━━━━━━

├ Volume: {data['volume_ratio']:.2f}x {'✅' if data['volume_ok'] else '⚠️'}
├ RSI: {data['rsi']:.2f} {'✅' if data['rsi_ok'] else '⚠️'}
├ MACD: {data['macd']:.4f}
└ ATR: ${data['atr']:.4f} ({data['atr'] / data['current_price'] * 100:.2f}%)

━━━━━━━━━━━━━━━━━━━━
🎯 <b>DYNAMIC TARGETS:</b>
━━━━━━━━━━━━━━━━━━━━

🟢 Entry: ${targets['entry']:.6f}

🎯 TP1: ${targets['tp1']:.6f} (+{targets['tp1_percent']}%)
🎯 TP2: ${targets['tp2']:.6f} (+{targets['tp2_percent']}%)
🎯 TP3: ${targets['tp3']:.6f} (+{targets['tp3_percent']}%)

🔴 Stop Loss: ${targets['sl']:.6f} (-{targets['sl_percent']}%)

📊 R:R Ratio: {targets['tp1_percent']/targets['sl_percent']:.2f}

━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
"""
    
    def run_scan(self):
        pairs = self.get_usdt_pairs()
        if not pairs:
            return 0
        
        logging.info(f"🔍 Scanning {len(pairs)} pairs for MA7/MA25 crossover...")
        found = 0
        
        for symbol in pairs:
            try:
                df = self.get_ohlcv_data(symbol)
                if df is None:
                    continue
                
                df = self.calculate_indicators(df)
                data = self.check_ma7_ma25_crossover(df)
                
                if data['signal']:
                    targets = self.calculate_dynamic_targets(df, data['current_price'])
                    msg = self.format_message(symbol, data, targets)
                    
                    if self.telegram.send_message(msg):
                        found += 1
                        self.signals_count += 1
                        logging.info(f"🚀 {symbol} | MA7/MA25 Cross | Vol: {data['volume_ratio']:.2f}x")
                
                self.analyzed_pairs.add(symbol)
                
            except Exception as e:
                logging.error(f"❌ Error {symbol}: {e}")
                continue
        
        logging.info(f"✅ Done. Found {found} MA7/MA25 signals")
        return found
    
    def send_startup(self):
        msg = f"""
🤖 <b>MA7/MA25 CROSSOVER BOT</b>

✅ Bot Started
📊 200 USDT pairs
🟡 MA7 (Yellow Line)
💗 MA25 (Dark Pink Line)
⏱️ Scan: Every {CONFIG['scan_interval_minutes']} min

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
📈 {self.signals_count} MA7/MA25 signals
"""
        return self.telegram.send_message(msg)
    
    def run(self):
        logging.info("🚀 Starting MA7/MA25 Crossover Bot...")
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
    print("🤖 MA7/MA25 CROSSOVER TRADING BOT")
    print("=" * 60 + "\n")
    
    if not validate_config():
        sys.exit(1)
    
    bot = BinanceScanner(CONFIG)
    bot.run()

if __name__ == "__main__":
    main()
