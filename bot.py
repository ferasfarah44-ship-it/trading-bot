import requests
import time
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = [
"SOLUSDT","ETHUSDT","ARBUSDT","LINKUSDT","NEARUSDT",
"OPUSDT","BTCUSDT","BNBUSDT","ADAUSDT","AVAXUSDT"
]

def send(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram variables missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(url,json={
            "chat_id":CHAT_ID,
            "text":msg
        })
        print("telegram:",r.status_code)
    except Exception as e:
        print("telegram error:",e)

def get_klines(symbol):

    url="https://api.binance.com/api/v3/klines"

    params={
        "symbol":symbol,
        "interval":"15m",
        "limit":100
    }

    r=requests.get(url,params=params)

    data=r.json()

    closes=[float(x[4]) for x in data]

    return closes

def rsi(data,period=14):

    gains=[]
    losses=[]

    for i in range(1,len(data)):
        diff=data[i]-data[i-1]

        if diff>0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain=sum(gains[-period:])/period
    avg_loss=sum(losses[-period:])/period

    if avg_loss==0:
        return 100

    rs=avg_gain/avg_loss

    return 100-(100/(1+rs))

def ema(data,period):

    k=2/(period+1)

    ema_val=data[0]

    for price in data[1:]:
        ema_val=price*k+ema_val*(1-k)

    return ema_val

def analyze(symbol):

    closes=get_klines(symbol)

    price=closes[-1]

    r=rsi(closes)

    ema9=ema(closes[-9:],9)
    ema21=ema(closes[-21:],21)

    if r<35 and ema9>ema21:

        return f"""
🚀 فرصة سكالبينغ

العملة: {symbol}

السعر: {price}

RSI: {round(r,2)}

الاتجاه: صعود
"""

    if r>70 and ema9<ema21:

        return f"""
⚠️ احتمال هبوط

العملة: {symbol}

السعر: {price}

RSI: {round(r,2)}
"""

    return None

send("🚀 بوت تحليل العملات بدأ العمل")

while True:

    try:

        for symbol in SYMBOLS:

            signal=analyze(symbol)

            if signal:
                send(signal)

            time.sleep(2)

        print("cycle done")

        time.sleep(900)

    except Exception as e:

        print("error:",e)
