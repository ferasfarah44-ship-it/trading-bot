import requests
import time
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

TELEGRAM_BOT_TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID=os.environ.get("TELEGRAM_CHAT_ID")

SYMBOLS=[
"SOLUSDT","LINKUSDT","ETHUSDT","XRPUSDT","NEARUSDT",
"ARBUSDT","OPUSDT","APTUSDT","AVAXUSDT","BTCUSDT"
]

TIMEFRAMES={"scalp":"15m","daily":"4h"}

last_signal={}

def send_msg(text):

    try:
        requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id":TELEGRAM_CHAT_ID,"text":text,"parse_mode":"HTML"},
        timeout=10)
    except:
        pass


def fetch_klines(symbol,interval,limit=200):

    try:

        r=requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol":symbol,"interval":interval,"limit":limit},
        timeout=10)

        if r.status_code!=200:
            return [],[],[],[]

        data=r.json()

        if not isinstance(data,list) or len(data)==0:
            return [],[],[],[]

        closes=[]
        highs=[]
        lows=[]
        volumes=[]

        for x in data:

            if len(x)>=6:

                closes.append(float(x[4]))
                highs.append(float(x[2]))
                lows.append(float(x[3]))
                volumes.append(float(x[5]))

        return closes,highs,lows,volumes

    except:
        return [],[],[],[]


def ema(data,p):

    k=2/(p+1)

    r=[data[0]]

    for price in data[1:]:

        r.append(price*k+r[-1]*(1-k))

    return r


def rsi(closes,p=14):

    gains=[]
    losses=[]

    for i in range(1,len(closes)):

        diff=closes[i]-closes[i-1]

        gains.append(max(diff,0))
        losses.append(max(-diff,0))

    if len(gains)<p:
        return 50

    ag=sum(gains[-p:])/p
    al=sum(losses[-p:])/p

    if al==0:
        return 100

    rs=ag/al

    return 100-(100/(1+rs))


def bollinger(closes,p=20):

    if len(closes)<p:
        return 0,0,0

    win=closes[-p:]

    mid=sum(win)/p

    std=(sum((x-mid)**2 for x in win)/p)**0.5

    up=mid+2*std
    low=mid-2*std

    return up,mid,low


def atr(highs,lows,closes,p=14):

    trs=[]

    for i in range(1,len(closes)):

        tr=max(

        highs[i]-lows[i],

        abs(highs[i]-closes[i-1]),

        abs(lows[i]-closes[i-1]))

        trs.append(tr)

    if len(trs)<p:
        return closes[-1]*0.005

    return sum(trs[-p:])/p


def analyze(symbol,interval,mode):

    closes,highs,lows,volumes=fetch_klines(symbol,interval)

    if len(closes)<60:
        return None

    price=closes[-1]

    ema9=ema(closes,9)
    ema21=ema(closes,21)
    ema50=ema(closes,50)

    r=rsi(closes)

    bb_up,bb_mid,bb_low=bollinger(closes)

    atr_val=atr(highs,lows,closes)

    vol_avg=sum(volumes[-20:])/20
    vol_ratio=volumes[-1]/vol_avg if vol_avg>0 else 1

    buy=0
    sell=0

    if ema9[-1]>ema21[-1]:
        buy+=1
    else:
        sell+=1

    if r<55:
        buy+=1

    if r>65:
        sell+=1

    if price>ema50[-1]:
        buy+=1
    else:
        sell+=1

    if price<=bb_low*1.01:
        buy+=2

    if price>=bb_up*0.99:
        sell+=2

    if vol_ratio>1.5:
        buy+=1
        sell+=1

    # كشف الضغط قبل الانفجار
    squeeze=False

    if (bb_up-bb_low)/price<0.04:
        squeeze=True

    if buy>sell:
        direction="BUY"
    elif sell>buy:
        direction="SELL"
    else:
        return None

    entry=price

    if direction=="BUY":

        sl=entry-1.5*atr_val
        t1=entry+atr_val
        t2=entry+2*atr_val
        t3=entry+3*atr_val

    else:

        sl=entry+1.5*atr_val
        t1=entry-atr_val
        t2=entry-2*atr_val
        t3=entry-3*atr_val

    if symbol in last_signal:

        if abs(entry-last_signal[symbol])/entry<0.003:
            return None

    last_signal[symbol]=entry

    return{

    "symbol":symbol,
    "direction":direction,
    "mode":mode,
    "tf":interval,
    "price":round(price,6),
    "entry":round(entry,6),
    "sl":round(sl,6),
    "t1":round(t1,6),
    "t2":round(t2,6),
    "t3":round(t3,6),
    "rsi":round(r,1),
    "vol":round(vol_ratio,2),
    "squeeze":squeeze
    }


def format_msg(s):

    d="🟢 BUY" if s["direction"]=="BUY" else "🔴 SELL"

    extra=""

    if s["squeeze"]:
        extra="⚠️ احتمال حركة قوية قادمة\n"

    if s["vol"]>2:
        extra+="🔥 حجم تداول مرتفع\n"

    return(

f"""{d} {s['symbol']}

{extra}

السعر {s['price']}

الدخول {s['entry']}

وقف الخسارة {s['sl']}

🎯 هدف1 {s['t1']}
🎯 هدف2 {s['t2']}
🎯 هدف3 {s['t3']}

RSI {s['rsi']} | VOL {s['vol']}

{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"""
)


def run_cycle():

    for symbol in SYMBOLS:

        for mode,tf in TIMEFRAMES.items():

            try:

                s=analyze(symbol,tf,mode)

                if s:

                    send_msg(format_msg(s))

                    time.sleep(1)

            except Exception as e:

                logger.error(e)


def main():

    send_msg("🚀 البوت بدأ العمل ويراقب السوق")

    cycle=0

    while True:

        start=time.time()

        cycle+=1

        run_cycle()

        if cycle%4==0:

            send_msg("💓 البوت يعمل بشكل طبيعي")

        elapsed=time.time()-start

        sleep=max(0,900-elapsed)

        time.sleep(sleep)


if __name__=="__main__":

    main()
