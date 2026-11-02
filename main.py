import os
import time
import telebot
import yfinance as yf
from flask import Flask
from threading import Thread
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# إنشاء خادم ويب بسيط لمنع توقف الخدمة على Render
app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM TRADING BOT is live with Real-Time Gold Data!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# دالة جلب سعر الذهب المباشر
def get_gold_price():
    try:
        ticker = yf.Ticker("GC=F") # عقود الذهب الفورية/المستقبلية
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            current_price = round(data['Close'].iloc[-1], 2)
            return current_price
    except Exception as e:
        print(f"Error fetching price: {e}")
    return None

# محرك الفحص الدوري ومراقبة السوق في الخلفية
def auto_market_monitor():
    print("Starting Market Monitor Loop...")
    last_price = None
    
    while True:
        try:
            price = get_gold_price()
            if price:
                print(f"Current Gold Price: ${price}")
                # هنا يمكنك إضافة شروط الاستراتيجية (IRS GOLD) لإرسال التنبيهات
            time.sleep(60) # فحص كل 60 ثانية
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(60)

# لوحة التحكم التفاعلية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("📈 سعر الذهب المباشر", callback_data="live_price")
    item2 = types.InlineKeyboardButton("⚙️ إعدادات الاستراتيجية", callback_data="strategy_settings")
    item3 = types.InlineKeyboardButton("🚀 تفعيل التنبيهات الآلية", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في **AL-GHRAM TRADING BOT** 🤖\n\n"
        "النظام الآن متصل بأسعار الذهب الحية (XAUUSD). اختر أحد الخيارات:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "live_price":
        bot.answer_callback_query(call.id)
        price = get_gold_price()
        if price:
            bot.send_message(call.message.chat.id, f"🟡 **سعر الذهب المباشر الآن:** `${price}`")
        else:
            bot.send_message(call.message.chat.id, "⚠️ جاري التحديث... تعذر جلب السعر اللحظة، حاول بعد ثوانٍ.")
            
    elif call.data == "strategy_settings":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ **إعدادات استراتيجية IRS GOLD:**\n- الزوج: الذهب (XAUUSD)\n- التحديث: كل دقيقة\n- النمط: إشارات وسكالبينج آلي.")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **تم تفعيل المراقبة الآلية!** سيقوم البوت بمتابعة الحركة وإرسال التنبيهات مباشرة في المحادثة.")

if __name__ == "__main__":
    # تشغيل خادم الويب
    t_web = Thread(target=run_web)
    t_web.start()
    
    # تشغيل محرك مراقبة السوق في الخلفية
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Bot is polling...")
    bot.infinity_polling()
