import os
import time
import asyncio
import requests
import pandas as pd
import pandas_ta as ta
from telegram import Bot

# إعدادات تليجرام فقط (يتم وضعها في Railway Variables)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

bot = Bot(token=TELEGRAM_TOKEN)

# العملات المطلوبة (مقابل USDT)
SYMBOLS = ['SOLUSDT', 'ETHUSDT', 'OPUSDT', 'NEARUSDT', 'ARBUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT']

async def send_msg(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_public_data(symbol):
    """جلب بيانات الشموع من بايننس بدون API Key"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    response = requests.get(url)
    data = response.json()
    
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def analyze_market(symbol):
    try:
        df = get_public_data(symbol)
        
        # مؤشر القوة النسبية (RSI) - لمعرفة قوة الزخم
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # المتوسطات المتحركة (SMA)
        df['MA7'] = ta.sma(df['close'], length=7)
        df['MA25'] = ta.sma(df['close'], length=25)
        
        cp = df['close'].iloc[-1]  # السعر الحالي
        rsi = df['RSI'].iloc[-1]
        ma7 = df['MA7'].iloc[-1]
        ma25 = df['MA25'].iloc[-1]
        
        # شروط الدخول "المطمئنة" (اتجاه صاعد + زخم شراء)
        if cp > ma7 and ma7 > ma25 and rsi > 55:
            target1 = cp * 1.03  # +3%
            target2 = cp * 1.06  # +6%
            return {
                "price": cp,
                "rsi": rsi,
                "t1": target1,
                "t2": target2
            }
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
    return None

async def main_loop():
    await send_msg("🚀 **تم تشغيل رادار العملات بنجاح**\nالبوت يحلل الآن بدون مفاتيح API.")
    last_health_check = time.time()

    while True:
        try:
            for symbol in SYMBOLS:
                signal = analyze_market(symbol)
                if signal:
                    msg = (f"📈 **إشارة صعود قوية: {symbol}**\n"
                           f"💰 السعر الحالي: `{signal['price']:.4f}`\n"
                           f"🔥 قوة الزخم (RSI): `{signal['rsi']:.2f}`\n\n"
                           f"🎯 هدف أول (+3%): `{signal['t1']:.4f}`\n"
                           f"🎯 هدف ثاني (+6%): `{signal['t2']:.4f}`\n"
                           f"🚀 الحالة: اتجاه صاعد مؤكد")
                    await send_msg(msg)
                
            # رسالة التأكد كل ساعة
            if time.time() - last_health_check > 3600:
                await send_msg("✅ **تحديث الساعة:** البوت يعمل ويحلل السوق حالياً.")
                last_health_check = time.time()
            
            await asyncio.sleep(60) # فحص السوق كل دقيقة
        except Exception as e:
            print(f"Loop Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main_loop())
