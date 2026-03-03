import os
import telebot
import time

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "🚀 البوت يعمل بثبات على Railway")

def run():
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            print("Bot started polling...")
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True
            )
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)

if __name__ == "__main__":
    run()
