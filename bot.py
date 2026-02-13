import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import requests
import time

# ================= الإعدادات =================
BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"

# ================= الأوامر التفاعلية =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟢 تشغيل الرادار", callback_data='start_scan')],
        [InlineKeyboardButton("🛑 إيقاف المؤقت", callback_data='stop_scan')],
        [InlineKeyboardButton("🔍 فحص سريع", callback_data='quick_scan')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🎮 لوحة تحكم الرادار المطور:', reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_scan':
        await query.edit_message_text(text="✅ تم تفعيل التشغيل التلقائي. الرادار يراقب السوق الآن.")
    elif query.data == 'stop_scan':
        await query.edit_message_text(text="🛑 تم إيقاف الرادار مؤقتاً.")
    elif query.data == 'quick_scan':
        await query.edit_message_text(text="🔎 جاري فحص جميع العملات... (ستصلك النتائج فوراً)")

# ================= التشغيل =================

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("البوت يعمل الآن مع أزرار حقيقية...")
    application.run_polling()

if __name__ == '__main__':
    main()
