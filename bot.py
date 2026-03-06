import requests
import os
import time

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram variables missing")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    try:
        r = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg
        })
        print("telegram status:", r.status_code)
    except Exception as e:
        print("telegram error:", e)

print("Bot started")

send("البوت يعمل الآن ✅")

while True:
    try:
        print("bot running...")
        time.sleep(300)
        send("البوت ما زال يعمل")
        
    except Exception as e:
        print("loop error:", e)
