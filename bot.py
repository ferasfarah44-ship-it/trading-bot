import os
import requests

print("BOT STARTED...")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
data = {
    "chat_id": CHAT_ID,
    "text": "البوت اشتغل بنجاح ✅"
}

response = requests.post(url, data=data)
print("Telegram response:", response.text)
