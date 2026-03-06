import requests
import os

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT  = os.environ.get("TELEGRAM_CHAT_ID")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

requests.post(url, json={
    "chat_id": CHAT,
    "text": "البوت اشتغل ✅"
})
