import os
import telebot
import time
import requests

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "🚀 البوت يعمل بثبات 24/7")

def run_bot():
    while True:
        try:
            print("Starting polling...")
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True
            )
        except requests.exceptions.ConnectionError as e:
            print("Connection lost. Retrying in 5 sec...")
            time.sleep(5)
        except Exception as e:
            print("Unexpected error:", e)
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
