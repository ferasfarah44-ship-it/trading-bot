import requests

TELEGRAM_TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

data = {
    "chat_id": CHAT_ID,
    "text": "BOT TEST SUCCESS"
}

print(requests.post(url, data=data).text)
