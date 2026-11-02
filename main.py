import os
import telebot
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

USER_CHAT_ID = None

app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM TRADING BOT - TradingView Webhook Edition is Active!"

# 🔗 مسار استقبال تنبيهات تريندنج فيو (Webhook)
@app.route('/webhook', methods=['POST'])
def webhook():
    global USER_CHAT_ID
    try:
        data = request.json
        if data and USER_CHAT_ID:
            # استلام الرسالة القادمة مباشرة من شارت CFD على تريندنج فيو
            action = data.get('action', 'SIGNAL')
            current_price = data.get('price', '0.00')
            entry = data.get('entry', '0.00')
            sl = data.get('sl', '0.00')
            tp = data.get('tp', '0.00')
            
            # بناء الرسالة النظيفة والخالية من الضجيج (العناصر الأربعة فقط)
            alert_msg = (
                f"💎 **IRS GOLD - {action}** 💎\n\n"
                f"🟡 السعر الحالي: `{current_price}`\n"
                f"🎯 الدخول المعلق: `{entry}`\n"
                f"🔴 وقف الخسارة (SL): `{sl}`\n"
                f"🟢 جني الأرباح (TP): `{tp}`"
            )
            
            bot.send_message(USER_CHAT_ID, alert_msg, parse_mode="Markdown")
            return "Success", 200
    except Exception as e:
        print(f"Webhook error: {e}")
    return "Error", 400

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    global USER_CHAT_ID
    USER_CHAT_ID = bot_message.chat.id
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في المقر الرئيسي لـ **IRS GOLD (TradingView Webhook Edition)** 🤖\n\n"
        "البوت الآن جاهز لاستقبال تنبيهات شارت الـ CFD الخاص بك مباشرة بدقة 100% وبدون أي فارق في الأسعار!",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    from threading import Thread
    t_web = Thread(target=run_web)
    t_web.start()
    
    print("Webhook Bot is running successfully...")
    bot.infinity_polling()
