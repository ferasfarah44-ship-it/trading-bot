import time
import requests
import numpy as np

# === الإعدادات ===
TELEGRAM_BOT_TOKEN = '8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0'
TELEGRAM_CHAT_ID = '7960335113'

# العملات للمراقبة
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT']

BINANCE_PUBLIC_API = "https://api.binance.com"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("خطأ في التلجرام:", e)

def get_klines(symbol, interval='5m', limit=50):
    url = f"{BINANCE_PUBLIC_API}/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"فشل جلب بيانات {symbol}: {response.status_code}")
        return []

def calculate_rsi(prices, window=14):
    prices = np.array(prices)
    if len(prices) < window + 1:
        return 50
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:window])
    avg_loss = np.mean(losses[:window])

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    for i in range(window, len(gains)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        if avg_loss == 0:
            rs = float('inf')
        else:
            rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_symbol(symbol):
    try:
        klines = get_klines(symbol, interval='5m', limit=50)
        if len(klines) < 20:
            return

        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        highs = [float(k[2]) for k in klines]

        current_price = closes[-1]
        prev_price = closes[-2]
        price_change_pct = (current_price - prev_price) / prev_price * 100

        # RSI
        rsi = calculate_rsi(closes[-15:])

        # الحجم
        current_volume = volumes[-1]
        avg_volume = sum(volumes[-10:-1]) / 9
        high_volume = current_volume > (avg_volume * 1.5)

        # اختراق مقاومة
        recent_high = max(highs[-11:-1])
        breakout = current_price > recent_high

        # الشروط (بدون دفتر أوامر)
        strong_bullish = price_change_pct > 2.0
        rsi_not_overbought = rsi < 60

        if strong_bullish and high_volume and breakout and rsi_not_overbought:
            coin = symbol.replace('USDT', '')
            msg = (
                f"🟢 <b>فرصة شراء!</b>\n"
                f"العملة: {coin}/USDT\n"
                f"السعر: ${current_price:.4f}\n"
                f"الارتفاع: +{price_change_pct:.2f}%\n"
                f"الحجم: {current_volume:,.0f}\n"
                f"RSI: {rsi:.1f}\n"
                f"الوقت: {time.strftime('%Y-%m-%d %H:%M')}"
            )
            send_telegram_message(msg)
            print(f"[+] إشارة لـ {coin}!")

    except Exception as e:
        print(f"خطأ في {symbol}: {e}")

def main():
    print("🚀 بدء المراقبة (بدون API Key)...")
    send_telegram_message("🤖 البوت يعمل: يراقب فرص الشراء بدون استخدام API Key!")
    while True:
        for symbol in SYMBOLS:
            analyze_symbol(symbol)
        time.sleep(60)

if __name__ == "__main__":
    main()
