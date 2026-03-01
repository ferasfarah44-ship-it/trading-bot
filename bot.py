import os
import time
import logging
import asyncio
from datetime import datetime
import pandas as pd
import ccxt.async_support as ccxt
from telegram import Bot
from dotenv import load_dotenv
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.volatility import BollingerBands

# ==============================
# LOAD ENV
# ==============================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))

TRADING_PAIRS = ['SOL/USDT', 'ETH/USDT', 'ARB/USDT', 'OP/USDT', 'NEAR/USDT', 'XPR/USDT']

# ==============================
# LOGGING (مضمون يطبع)
# ==============================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True
)
logger = logging.getLogger()

# ==============================
# BOT CLASS
# ==============================
class TradingSignalBot:

    def __init__(self):

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            raise ValueError("❌ Telegram credentials missing in .env")

        self.exchange = ccxt.binance({
            "enableRateLimit": True,
            "timeout": 20000,
            "options": {"defaultType": "spot"}
        })

        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.last_signals = {}

        logger.info("✅ Bot initialized")

    async def fetch_ohlcv(self, symbol):
        try:
            logger.debug(f"Fetching {symbol}")
            ohlcv = await self.exchange.fetch_ohlcv(symbol, "1h", limit=100)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except Exception as e:
            logger.error(f"❌ Fetch error {symbol}: {e}")
            return None

    def calculate_indicators(self, df):

        df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()

        macd = MACD(close=df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        df["sma_20"] = SMAIndicator(close=df["close"], window=20).sma_indicator()
        df["sma_50"] = SMAIndicator(close=df["close"], window=50).sma_indicator()
        df["ema_12"] = EMAIndicator(close=df["close"], window=12).ema_indicator()
        df["ema_26"] = EMAIndicator(close=df["close"], window=26).ema_indicator()

        bb = BollingerBands(close=df["close"])
        df["bb_high"] = bb.bollinger_hband()
        df["bb_low"] = bb.bollinger_lband()

        stoch = StochasticOscillator(
            high=df["high"],
            low=df["low"],
            close=df["close"]
        )
        df["stoch_k"] = stoch.stoch()

        return df

    def analyze_signal(self, df, symbol):

        if df is None or len(df) < 50:
            return None

        current = df.iloc[-1]
        prev = df.iloc[-2]

        buy = 0
        sell = 0

        # RSI
        if current["rsi"] < 30:
            buy += 2
        elif current["rsi"] > 70:
            sell += 2
        elif 40 < current["rsi"] < 60 and prev["rsi"] < 40:
            buy += 1

        # MACD
        if current["macd"] > current["macd_signal"] and prev["macd"] <= prev["macd_signal"]:
            buy += 2
        elif current["macd"] < current["macd_signal"] and prev["macd"] >= prev["macd_signal"]:
            sell += 2

        # MA
        if current["close"] > current["sma_20"] > current["sma_50"]:
            buy += 1
        elif current["close"] < current["sma_20"] < current["sma_50"]:
            sell += 1

        # EMA
        if current["ema_12"] > current["ema_26"] and prev["ema_12"] <= prev["ema_26"]:
            buy += 2

        # BB
        if current["close"] < current["bb_low"]:
            buy += 1
        elif current["close"] > current["bb_high"]:
            sell += 1

        # STOCH
        if current["stoch_k"] < 20 and current["stoch_k"] > prev["stoch_k"]:
            buy += 1
        elif current["stoch_k"] > 80:
            sell += 1

        signal = None
        if buy >= 3:
            signal = "BUY"
        elif sell >= 3:
            signal = "SELL"

        if not signal:
            return None

        price = current["close"]

        return {
            "symbol": symbol,
            "signal": signal,
            "price": price,
            "sl": price * (0.95 if signal == "BUY" else 1.05),
            "tp1": price * (1.03 if signal == "BUY" else 0.97),
            "tp2": price * (1.06 if signal == "BUY" else 0.94),
            "tp3": price * (1.10 if signal == "BUY" else 0.90),
        }

    async def send_signal(self, data):

        try:
            msg = f"""
🚨 SIGNAL

Pair: {data['symbol']}
Type: {data['signal']}
Price: {data['price']:.4f}

SL: {data['sl']:.4f}
TP1: {data['tp1']:.4f}
TP2: {data['tp2']:.4f}
TP3: {data['tp3']:.4f}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=msg
            )

            logger.info(f"✅ Sent {data['symbol']} {data['signal']}")

        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")

    async def check_pair(self, symbol):

        df = await self.fetch_ohlcv(symbol)
        if df is None:
            return

        df = self.calculate_indicators(df)
        signal = self.analyze_signal(df, symbol)

        if not signal:
            logger.debug(f"No signal {symbol}")
            return

        last = self.last_signals.get(symbol)
        if last and (datetime.now() - last).total_seconds() < 3600:
            return

        await self.send_signal(signal)
        self.last_signals[symbol] = datetime.now()

    async def run(self):

        logger.info("🚀 Bot started")

        try:
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="🤖 Bot Started Successfully"
            )
        except Exception as e:
            logger.error(f"Startup Telegram error: {e}")

        while True:
            try:
                tasks = [self.check_pair(p) for p in TRADING_PAIRS]
                await asyncio.gather(*tasks)
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        await self.exchange.close()
        logger.info("Bot stopped")

# ==============================
# MAIN
# ==============================
async def main():
    bot = TradingSignalBot()
    try:
        await bot.run()
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
