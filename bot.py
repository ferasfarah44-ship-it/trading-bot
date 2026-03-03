import os
import telebot
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "🚀 البوت يعمل بثبات على Railway")

@app.route('/', methods=['GET'])
def home():
    return "Bot is running", 200

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    WEBHOOK_URL = os.getenv("RAILWAY_STATIC_URL")

    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

    app.run(host="0.0.0.0", port=PORT)
