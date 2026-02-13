import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import requests

# ================= الإعدادات =================
BOT_TOKEN = "8452767198:AAG7JIWMBIkK21L8ihNd-O7AQYOXtXZ4lm0"
CHAT_ID = "7960335113"

# ================= لوحة التحكم =================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🟢 تشغيل الرادار", callback_data='start'), InlineKeyboardButton("🛑 إيقاف", callback_data='stop')],
        [InlineKeyboardButton("🔍 فحص الآن", callback_data='scan'), InlineKeyboardButton("📊 الحالة", callback_data='status')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ **أهلاً بك في رادار الانفجار السعري.**\nاستخدم الأزرار للتحكم:", 
                                   reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start':
        await query.edit_message_text("🟢 **تم تفعيل التشغيل التلقائي.**\nالبوت يبحث عن فرص الآن...", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif query.data == 'scan':
        await query.edit_message_text("🔎 **جاري فحص العملات...**\nسأوافيك بأي فرصة فور ظهورها.", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif query.data == 'status':
        await query.edit_message_text("✅ **الحالة: متصل**\nالسيرفر: Railway\nالنظام: يعمل بكفاءة.", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif query.data == 'stop':
        await query.edit_message_text("🛑 **تم إيقاف التنبيهات مؤقتاً.**", reply_markup=get_main_keyboard(), parse_mode="Markdown")

# ================= التشغيل الرئيسي =================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_tap))
    
    print("🚀 البوت يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()
