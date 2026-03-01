import os
import time
import logging
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np
import ccxt.async_support as ccxt
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv
import ta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.volatility import BollingerBands

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # 5 minutes default

# Trading pairs
TRADING_PAIRS = ['SOL/USDT', 'ETH/USDT', 'ARB/USDT', 'OP/USDT', 'NEAR/USDT', 'XPR/USDT']

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingSignalBot:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.last_signals = {}  # Track last signal time for each pair
        
    async def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        """Fetch OHLCV data"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # RSI
        df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
        
        # MACD
        macd = MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Moving Averages
        df['sma_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['sma_50'] = SMAIndicator(close=df['close'], window=50).sma_indicator()
        df['ema_12'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
        df['ema_26'] = EMAIndicator(close=df['close'], window=26).ema_indicator()
        
        # Bollinger Bands
        bb = BollingerBands(close=df['close'])
        df['bb_high'] = bb.bollinger_hband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_low'] = bb.bollinger_lband()
        
        # Stochastic
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        return df
    
    def analyze_signal(self, df, symbol):
        """Analyze and generate trading signal"""
        if df is None or len(df) < 50:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Current price
        current_price = current['close']
        
        # Signal conditions
        buy_signals = 0
        sell_signals = 0
        reasons = []
        
        # RSI conditions
        if current['rsi'] < 30:
            buy_signals += 2
            reasons.append(f"RSI Oversold: {current['rsi']:.2f}")
        elif current['rsi'] > 70:
            sell_signals += 2
            reasons.append(f"RSI Overbought: {current['rsi']:.2f}")
        elif 40 < current['rsi'] < 60 and prev['rsi'] < 40:
            buy_signals += 1
            reasons.append(f"RSI Rising: {current['rsi']:.2f}")
        
        # MACD conditions
        if current['macd'] > current['macd_signal'] and prev['macd'] <= prev['macd_signal']:
            buy_signals += 2
            reasons.append("MACD Bullish Crossover")
        elif current['macd'] < current['macd_signal'] and prev['macd'] >= prev['macd_signal']:
            sell_signals += 2
            reasons.append("MACD Bearish Crossover")
        
        # Moving Average conditions
        if current['close'] > current['sma_20'] > current['sma_50']:
            buy_signals += 1
            reasons.append("Price above SMA20 & SMA50")
        elif current['close'] < current['sma_20'] < current['sma_50']:
            sell_signals += 1
            reasons.append("Price below SMA20 & SMA50")
        
        # EMA crossover
        if current['ema_12'] > current['ema_26'] and prev['ema_12'] <= prev['ema_26']:
            buy_signals += 2
            reasons.append("EMA12/26 Bullish Cross")
        
        # Bollinger Bands
        if current['close'] < current['bb_low']:
            buy_signals += 1
            reasons.append(f"Price below BB Lower: {current['bb_low']:.2f}")
        elif current['close'] > current['bb_high']:
            sell_signals += 1
            reasons.append(f"Price above BB Upper: {current['bb_high']:.2f}")
        
        # Stochastic
        if current['stoch_k'] < 20 and current['stoch_k'] > prev['stoch_k']:
            buy_signals += 1
            reasons.append(f"Stochastic Oversold: {current['stoch_k']:.2f}")
        elif current['stoch_k'] > 80:
            sell_signals += 1
            reasons.append(f"Stochastic Overbought: {current['stoch_k']:.2f}")
        
        # Determine signal
        signal = None
        if buy_signals >= 3:
            signal = "BUY"
        elif sell_signals >= 3:
            signal = "SELL"
        
        if not signal:
            return None
        
        # Calculate targets
        atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
        
        if signal == "BUY":
            entry_price = current_price
            stop_loss = entry_price * 0.95  # 5% SL
            target1 = entry_price * 1.03    # 3% TP1
            target2 = entry_price * 1.06    # 6% TP2
            target3 = entry_price * 1.10    # 10% TP3
        else:
            entry_price = current_price
            stop_loss = entry_price * 1.05
            target1 = entry_price * 0.97
            target2 = entry_price * 0.94
            target3 = entry_price * 0.90
        
        return {
            'symbol': symbol,
            'signal': signal,
            'current_price': current_price,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target1': target1,
            'target2': target2,
            'target3': target3,
            'target1_pct': 3,
            'target2_pct': 6,
            'target3_pct': 10,
            'reasons': reasons,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'rsi': current['rsi'],
            'macd': current['macd'],
            'timestamp': datetime.now()
        }
    
    async def send_telegram_message(self, signal_data):
        """Send signal to Telegram"""
        try:
            message = f"""
🚨 **TRADING SIGNAL** 🚨

📊 **Pair:** {signal_data['symbol']}
📈 **Signal:** {signal_data['signal']}
💰 **Current Price:** ${signal_data['current_price']:.4f}

🎯 **ENTRY:** ${signal_data['entry_price']:.4f}

📉 **Stop Loss:** ${signal_data['stop_loss']:.4f}

🎯 **Targets:**
• TP1: ${signal_data['target1']:.4f} (+{signal_data['target1_pct']}%)
• TP2: ${signal_data['target2']:.4f} (+{signal_data['target2_pct']}%)
• TP3: ${signal_data['target3']:.4f} (+{signal_data['target3_pct']}%)

📊 **Technical Analysis:**
• RSI: {signal_data['rsi']:.2f}
• MACD: {signal_data['macd']:.4f}
• Buy Signals: {signal_data['buy_signals']}
• Sell Signals: {signal_data['sell_signals']}

📝 **Reasons:**
{chr(10).join('• ' + r for r in signal_data['reasons'])}

⏰ **Time:** {signal_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}

⚠️ **Risk Management:** Always use stop loss!
"""
            
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Signal sent for {signal_data['symbol']}: {signal_data['signal']}")
            
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def check_pair(self, symbol):
        """Check a single trading pair"""
        try:
            # Fetch data
            df = await self.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            if df is None:
                return
            
            # Calculate indicators
            df = self.calculate_indicators(df)
            
            # Analyze signal
            signal = self.analyze_signal(df, symbol)
            
            if signal:
                # Check if we already sent a signal recently (avoid spam)
                last_signal_time = self.last_signals.get(symbol)
                if last_signal_time:
                    time_diff = (datetime.now() - last_signal_time).total_seconds()
                    if time_diff < 3600:  # 1 hour cooldown
                        return
                
                # Send signal
                await self.send_telegram_message(signal)
                self.last_signals[symbol] = datetime.now()
                
        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")
    
    async def run(self):
        """Main loop"""
        logger.info("Trading Signal Bot started...")
        
        # Send startup message
        try:
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="🤖 **Trading Signal Bot Started**\n\nMonitoring: " + ", ".join(TRADING_PAIRS)
            )
        except:
            pass
        
        while True:
            try:
                logger.info(f"Checking {len(TRADING_PAIRS)} pairs...")
                
                tasks = [self.check_pair(pair) for pair in TRADING_PAIRS]
                await asyncio.gather(*tasks)
                
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Cleanup"""
        await self.exchange.close()
        logger.info("Bot stopped")

async def main():
    bot = TradingSignalBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
