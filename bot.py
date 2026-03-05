import requests
import time
import logging
import os
from datetime import datetime

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Environment Variables ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ─── العملات ─────────────────────────────────────────────────────────────────
SYMBOLS = [
    "SOLUSDT","LINKUSDT","ETHUSDT","XRPUSDT","NEARUSDT",
    "ARBUSDT","OPUSDT","APTUSDT","AVAXUSDT","BTCUSDT"
]

TIMEFRAMES = {"scalp": "15m", "daily": "4h"}

# ════════════════════════════════════════════════════════════════════════════════
# إرسال رسالة
# ════════════════════════════════════════════════════════════════════════════════
def send_msg(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing!")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        if r.status_code == 200:
            logger.info("✅ Message sent")
        else:
            logger.error(f"Telegram error {r.status_code}: {r.text}")
    except Exception as e:
        logger.error(f"send_msg exception: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# جلب البيانات من Binance (نسخة مصححة)
# ════════════════════════════════════════════════════════════════════════════════
def fetch_klines(symbol: str, interval: str, limit: int = 200):

    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10
        )

        if r.status_code != 200:
            logger.error(f"Binance HTTP error {r.status_code}")
            return [], [], [], []

        data = r.json()

        # تحقق أن البيانات قائمة شموع
        if not isinstance(data, list) or len(data) == 0:
            logger.warning(f"No kline data for {symbol}")
            return [], [], [], []

        closes  = []
        highs   = []
        lows    = []
        volumes = []

        for x in data:
            if len(x) >= 6:
                closes.append(float(x[4]))
                highs.append(float(x[2]))
                lows.append(float(x[3]))
                volumes.append(float(x[5]))

        return closes, highs, lows, volumes

    except Exception as e:
        logger.error(f"fetch_klines error {symbol} {interval}: {e}")
        return [], [], [], []

# ════════════════════════════════════════════════════════════════════════════════
# المؤشرات الفنية
# ════════════════════════════════════════════════════════════════════════════════
def ema(data, period):
    k = 2 / (period + 1)
    result = [data[0]]
    for price in data[1:]:
        result.append(price * k + result[-1] * (1 - k))
    return result

def rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return 50
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd_histogram(closes):
    if len(closes) < 35:
        return 0, 0
    fast   = ema(closes, 12)
    slow   = ema(closes, 26)
    macd_l = [f - s for f, s in zip(fast, slow)]
    signal = ema(macd_l, 9)
    hist   = [m - s for m, s in zip(macd_l, signal)]
    return hist[-1], hist[-2] if len(hist) > 1 else 0

def bollinger(closes, period=20, mult=2.0):
    if len(closes) < period:
        return 0, 0, 0
    window = closes[-period:]
    mid    = sum(window) / period
    std    = (sum((x - mid)**2 for x in window) / period) ** 0.5
    return mid + mult * std, mid, mid - mult * std

def atr(highs, lows, closes, period=14):
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i]  - closes[i-1])
        )
        trs.append(tr)
    if len(trs) < period:
        return closes[-1] * 0.005
    return sum(trs[-period:]) / period

def stochastic(highs, lows, closes, k_period=14):
    if len(closes) < k_period + 1:
        return 50, 50
    lowest  = min(lows[-k_period:])
    highest = max(highs[-k_period:])
    if highest == lowest:
        return 50, 50
    k = 100 * (closes[-1] - lowest) / (highest - lowest)
    low_prev  = min(lows[-k_period-1:-1])
    high_prev = max(highs[-k_period-1:-1])
    rng_prev  = high_prev - low_prev or 1
    k_prev    = 100 * (closes[-2] - low_prev) / rng_prev
    return k, k_prev

# ════════════════════════════════════════════════════════════════════════════════
# منطق الإشارة
# ════════════════════════════════════════════════════════════════════════════════
def analyze(symbol: str, interval: str, mode: str):

    closes, highs, lows, volumes = fetch_klines(symbol, interval)

    if len(closes) < 50:
        return None

    price             = closes[-1]
    ema9_v            = ema(closes, 9)
    ema21_v           = ema(closes, 21)
    ema50_v           = ema(closes, 50)
    rsi_val           = rsi(closes)
    macd_h, macd_prev = macd_histogram(closes)
    bb_up, _, bb_low  = bollinger(closes)
    atr_val           = atr(highs, lows, closes)
    k_val, k_prev     = stochastic(highs, lows, closes)

    vol_avg   = sum(volumes[-20:]) / 20
    vol_ratio = volumes[-1] / vol_avg if vol_avg > 0 else 1

    buy = sell = 0

    if ema9_v[-1] > ema21_v[-1] and ema9_v[-2] <= ema21_v[-2]: buy += 2
    elif ema9_v[-1] > ema21_v[-1]: buy += 1

    if ema9_v[-1] < ema21_v[-1] and ema9_v[-2] >= ema21_v[-2]: sell += 2
    elif ema9_v[-1] < ema21_v[-1]: sell += 1

    if rsi_val < 35: buy += 2
    elif rsi_val < 55: buy += 1

    if rsi_val > 70: sell += 2
    elif rsi_val > 60: sell += 1

    if macd_h > 0 and macd_h > macd_prev: buy += 2
    elif macd_h > macd_prev: buy += 1

    if macd_h < 0 and macd_h < macd_prev: sell += 2
    elif macd_h < macd_prev: sell += 1

    if price <= bb_low * 1.01: buy += 2
    if price >= bb_up * 0.99: sell += 2

    if k_val < 30 and k_val > k_prev: buy += 2
    elif k_val > k_prev: buy += 1

    if k_val > 70 and k_val < k_prev: sell += 2
    elif k_val < k_prev: sell += 1

    if price > ema50_v[-1]: buy += 1
    else: sell += 1

    if vol_ratio > 1.5:
        if buy > sell: buy += 1
        else: sell += 1

    MIN = 6

    if buy >= MIN and buy > sell:
        direction = "BUY"
    elif sell >= MIN and sell > buy:
        direction = "SELL"
    else:
        return None

    entry = price

    if direction == "BUY":
        stop_loss = round(entry - 1.5 * atr_val, 6)
        t1 = round(entry + 1.0 * atr_val, 6)
        t2 = round(entry + 2.0 * atr_val, 6)
        t3 = round(entry + 3.5 * atr_val, 6)
    else:
        stop_loss = round(entry + 1.5 * atr_val, 6)
        t1 = round(entry - 1.0 * atr_val, 6)
        t2 = round(entry - 2.0 * atr_val, 6)
        t3 = round(entry - 3.5 * atr_val, 6)

    def pct(t): return round(abs(t - entry) / entry * 100, 2)

    return {
        "symbol": symbol,
        "direction": direction,
        "mode": mode,
        "timeframe": interval,
        "price": round(price, 6),
        "entry": round(entry, 6),
        "stop_loss": stop_loss,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "p1": pct(t1),
        "p2": pct(t2),
        "p3": pct(t3),
        "rsi": round(rsi_val, 1),
        "score": max(buy, sell),
        "vol_ratio": round(vol_ratio, 2),
    }

# ════════════════════════════════════════════════════════════════════════════════
# تنسيق الرسالة
# ════════════════════════════════════════════════════════════════════════════════
def format_signal(s: dict) -> str:

    d = "🟢 BUY" if s["direction"] == "BUY" else "🔴 SELL"
    m = "⚡ سكالب" if s["mode"] == "scalp" else "📅 يومي"

    return (
        f"{d} — <b>{s['symbol']}</b>\n"
        f"{m} | فريم: {s['timeframe']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 السعر الحالي:  <b>{s['price']}</b>\n"
        f"🎯 نقطة الدخول:   <b>{s['entry']}</b>\n"
        f"🛑 وقف الخسارة:   <b>{s['stop_loss']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"✅ هدف 1:  {s['t1']}  (+{s['p1']}%)\n"
        f"✅ هدف 2:  {s['t2']}  (+{s['p2']}%)\n"
        f"✅ هدف 3:  {s['t3']}  (+{s['p3']}%)\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 RSI: {s['rsi']} | حجم: {s['vol_ratio']}x | قوة: {s['score']}/14\n"
        f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
        f"⚠️ <i>للمعلومات فقط — ليست توصية استثمارية</i>"
    )

# ════════════════════════════════════════════════════════════════════════════════
# الحلقة الرئيسية
# ════════════════════════════════════════════════════════════════════════════════
def run_cycle():

    logger.info("🔍 Running analysis cycle...")

    for symbol in SYMBOLS:
        for mode, tf in TIMEFRAMES:

            try:
                sig = analyze(symbol, tf, mode)
                if sig:
                    send_msg(format_signal(sig))
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error {symbol} {mode}: {e}")

            time.sleep(0.3)

def send_heartbeat(cycle: int):

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    send_msg(
        f"💓 <b>البوت يعمل بشكل طبيعي</b>\n"
        f"🕐 {now}\n"
        f"📈 يراقب {len(SYMBOLS)} عملة | دورة #{cycle}\n"
        f"⚡ Scalp: 15m  |  📅 Daily: 4h"
    )

def main():

    logger.info("🚀 Bot starting...")

    send_msg(
        f"🚀 <b>بوت التحليل بدأ العمل!</b>\n"
        f"📊 SOL LINK ETH XRP NEAR ARB OP APT AVAX BTC\n"
        f"⚡ Scalp: 15m  |  📅 Daily: 4h\n"
        f"🔄 تحليل كل 15 دقيقة | 💓 تأكيد كل ساعة"
    )

    cycle = 0

    while True:

        start = time.time()

        cycle += 1

        logger.info(f"🔄 Cycle #{cycle}")

        run_cycle()

        if cycle % 4 == 0:
            send_heartbeat(cycle)

        elapsed = time.time() - start

        sleep_t = max(0, 15 * 60 - elapsed)

        logger.info(f"⏳ Next cycle in {sleep_t:.0f}s")

        time.sleep(sleep_t)

if __name__ == "__main__":
    main()
