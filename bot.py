import telebot
import time
import os

# ====== حط التوكن تبعك هون ======
TOKEN = os.getenv("BOT_TOKEN")  # الأفضل تحطه بمتغيرات Railway
# TOKEN = "حط_توكنك_هون_لو_بدك_مباشر"

print("BOT STARTED...")

bot = telebot.TeleBot(TOKEN)

# رسالة اختبار عند التشغيل
try:
    me = bot.get_me()
    print("Telegram response:", me)
except Exception as e:
    print("Telegram Error:", e)


# ====== أمر اختبار ======
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "البوت شغال ✅")


print("BOT RUNNING...")

# ====== تشغيل مستمر (مهم جداً لRailway) ======
bot.infinity_polling(timeout=60, long_polling_timeout=60)
