import os
import telebot

# قراءة التوكن بأمان من متغيرات البيئة في Render
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    bot.reply_to(bot_message, "أهلاً بك يا إدريس، بوت التداول (AL-GHRAM BOT) يعمل الآن بنجاح وبشكل آمن!")

# تشغيل البوت باستمرار
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
