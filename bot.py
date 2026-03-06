import requests
import os
import time

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT  = os.environ["TELEGRAM_CHAT_ID"]

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

while True:
    requests.post(url, json={
        "chat_id": CHAT,
        "text": "البوت يعمل الآن ✅"
    })

    print("message sent")

    time.sleep(60)
