import os
import telebot
from flask import Flask
from threading import Thread
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# إنشاء خادم ويب بسيط لمنع توقف الخدمة على Render
app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM TRADING BOT is live and running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# لوحة التحكم التفاعلية لاستراتيجية IRS GOLD
@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("📊 حالة السوق", callback_data="market_status")
    item2 = types.InlineKeyboardButton("⚙️ إعدادات الاستراتيجية", callback_data="strategy_settings")
    item3 = types.InlineKeyboardButton("🚀 تفعيل صفقات السكالبينج", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في لوحة تحكم **AL-GHRAM TRADING BOT** 🤖\n\n"
        "استراتيجية سكالبينج الذهب (IRS GOLD - جلسات لندن ونيويورك) جاهزة. اختر أحد الخيارات أدناه:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "market_status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📈 حالة السوق الحالية: بانتظار مزامنة الجلسات (لندن / نيويورك)... جاري رصد مستويات الذهب (XAUUSD).")
    elif call.data == "strategy_settings":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ إعدادات الاستراتيجية الحالية:\n- الزوج: XAUUSD (الذهب)\n- الأوامر: Buy-Stop & Sell-Stop\n- الأسلوب: سكالبينج آلي.")
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 تم تفعيل محرك الاستراتيجية! جاري الاستعداد لرفع الأوامر المعلقة.")

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    print("Bot and Web Server are running with IRS GOLD Engine...")
    bot.infinity_polling()
