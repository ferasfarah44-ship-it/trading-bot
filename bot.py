import os
import telebot
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

WEBHOOK_URL = os.getenv("RAILWAY_STATIC_URL")

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "🚀 البوت يعمل بنظام Webhook")

@bot.message_handler(commands=['price'])
def price(message):
    import requests
    r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
    price = r.json()["price"]
    bot.reply_to(message, f"💰 سعر BTC الحالي: {price} USD")

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
