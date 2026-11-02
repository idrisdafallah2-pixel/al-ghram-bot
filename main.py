import os
import telebot
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# إنشاء خادم ويب بسيط لمنع توقف الخدمة على Render
app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM BOT is running live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    bot.reply_to(bot_message, "أهلاً بك يا إدريس، بوت التداول (AL-GHRAM BOT) يعمل الآن بنجاح وبشكل آمن!")

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    print("Bot and Web Server are running...")
    bot.infinity_polling()
