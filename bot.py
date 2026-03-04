import os
import requests
import telebot
import time
import threading

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

SYMBOLS = [
"SOLUSDT",
"ETHUSDT",
"LINKUSDT",
"AVAXUSDT",
"NEARUSDT",
"ARBUSDT",
"OPUSDT",
"SUIUSDT"
]

CHAT_ID = None
last_sent = 0
last_heartbeat = time.time()


def get_klines(symbol):

    url=f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=40"
    data=requests.get(url).json()

    closes=[float(x[4]) for x in data]
    highs=[float(x[2]) for x in data]
    lows=[float(x[3]) for x in data]
    volumes=[float(x[5]) for x in data]

    return closes,highs,lows,volumes


def analyze(symbol):

    closes,highs,lows,volumes=get_klines(symbol)

    price=closes[-1]

    score=0
    reasons=[]

    # Momentum
    m1=(price-closes[-2])/closes[-2]
    m3=(price-closes[-4])/closes[-4]
    m5=(price-closes[-6])/closes[-6]

    momentum=(m1>0.006 or m3>0.011 or m5>0.018)

    if momentum:
        score+=1
        reasons.append("Momentum")

    # Breakout
    breakout=price>max(highs[-15:])

    if breakout:
        score+=1
        reasons.append("Breakout")

    # Compression
    range10=max(highs[-10:])-min(lows[-10:])
    compression=range10/price<0.004

    if compression:
        score+=1
        reasons.append("Compression")

    # Volume spike
    avg_volume=sum(volumes[:-1])/len(volumes[:-1])
    volume_spike=volumes[-1]>avg_volume*1.4

    if volume_spike:
        score+=1
        reasons.append("Volume Spike")

    # Whale volume
    whale_volume=volumes[-1]>avg_volume*2

    if whale_volume:
        score+=1
        reasons.append("Whale Volume")

    # Near resistance
    recent_high=max(highs[-30:])
    near_resistance=(recent_high-price)/price<0.004

    if near_resistance:
        score+=1
        reasons.append("Near Resistance")

    # Accumulation
    range20=max(highs[-20:])-min(lows[-20:])
    accumulation=range20/price<0.008

    if accumulation:
        score+=1
        reasons.append("Accumulation")

    if score>=2:

        return {
            "symbol":symbol,
            "price":price,
            "score":score,
            "reason":" + ".join(reasons)
        }

    return None


@bot.message_handler(commands=['start'])
def start(message):

    global CHAT_ID
    CHAT_ID=message.chat.id

    bot.reply_to(message,"🚀 البوت بدأ تحليل السوق")


def scanner():

    global last_sent,last_heartbeat

    while True:

        try:

            if CHAT_ID:

                signals=[]

                for symbol in SYMBOLS:

                    result=analyze(symbol)

                    if result:
                        signals.append(result)

                if signals:

                    best=max(signals,key=lambda x:x["score"])

                    now=time.time()

                    if now-last_sent>300:

                        bot.send_message(CHAT_ID,f"""
🚀 أفضل فرصة الآن

العملة: {best['symbol']}
السعر: {round(best['price'],4)}

القوة:
{best['score']} / 7

السبب:
{best['reason']}
""")

                        last_sent=now

                if time.time()-last_heartbeat>3600:

                    bot.send_message(CHAT_ID,"✅ البوت يعمل ويحلل السوق")

                    last_heartbeat=time.time()

        except Exception as e:

            print(e)

        time.sleep(30)


threading.Thread(target=scanner).start()

bot.infinity_polling()
