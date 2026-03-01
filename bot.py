import requests
import time

BOT_TOKEN = "PUT_YOUR_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

print("BOOTING...")

send_telegram("🚀 البوت اشتغل الآن")

while True:
    print("RUNNING LOOP")
    time.sleep(30)
