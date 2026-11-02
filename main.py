import os
import time
import telebot
import yfinance as yf
from flask import Flask
from threading import Thread
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# معرف الشات الخاص بك (سيتم التقاطه تلقائياً عند أول /start)
USER_CHAT_ID = None

# إنشاء خادم ويب بسيط لمنع توقف الخدمة على Render
app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM TRADING BOT is live with IRS GOLD Engine & Alerts!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# دالة جلب سعر الذهب المباشر
def get_gold_price():
    try:
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            current_price = round(data['Close'].iloc[-1], 2)
            return current_price
    except Exception as e:
        print(f"Error fetching price: {e}")
    return None

# محرك المراقبة الآلية وإرسال الإشارات المعلقة
def auto_market_monitor():
    global USER_CHAT_ID
    print("Starting IRS GOLD Strategy Monitor...")
    
    # للتجربة واختبار الإرسال الآلي، سنقوم بمتابعة تغيّر السعر
    last_checked_price = None
    
    while True:
        try:
            price = get_gold_price()
            if price and USER_CHAT_ID:
                print(f"Monitoring Gold Price: ${price}")
                
                # كمثال حي للاستراتيجية: إذا كان هناك تغير ملحوظ أو لاختبار الإرسال الآلي
                if last_checked_price is not None:
                    diff = round(price - last_checked_price, 2)
                    # يمكنك لاحقاً تعديل الشرط ليناسب شروط جلسة لندن أو نيويورك بدقة
                    if abs(diff) >= 0.5: 
                        signal_type = "🟢 BUY-STOP (شراء معلق)" if diff > 0 else "🔴 SELL-STOP (بيع معلق)"
                        alert_msg = (
                            f"🚨 **تنبيه إشارة سكالبينج آلي (IRS GOLD)** 🚨\n\n"
                            f"🟡 السعر الحالي: `${price}`\n"
                            f"📊 نوع الإشارة المقترحة: {signal_type}\n"
                            f"⚡ التغير اللحظي: `{diff}`\n\n"
                            f"جهز صفقتك الآن يا إدريس!"
                        )
                        bot.send_message(USER_CHAT_ID, alert_msg, parse_mode="Markdown")
                
                last_checked_price = price
                
            time.sleep(60) # الفحص كل دقيقة
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(60)

# لوحة التحكم التفاعلية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    global USER_CHAT_ID
    USER_CHAT_ID = bot_message.chat.id # حفظ معرفك تلقائياً لإرسال التنبيهات إليه
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("📈 سعر الذهب المباشر", callback_data="live_price")
    item2 = types.InlineKeyboardButton("⚙️ إعدادات الاستراتيجية", callback_data="strategy_settings")
    item3 = types.InlineKeyboardButton("🚀 تفعيل التنبيهات الآلية", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في لوحة تحكم **AL-GHRAM TRADING BOT** 🤖\n\n"
        "تم ربط محرك إشارات السكالبينج الآلي بنجاح. اختر أحد الخيارات أدناه:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global USER_CHAT_ID
    USER_CHAT_ID = call.message.chat.id
    
    if call.data == "live_price":
        bot.answer_callback_query(call.id)
        price = get_gold_price()
        if price:
            bot.send_message(call.message.chat.id, f"🟡 **سعر الذهب المباشر الآن:** `${price}`")
        else:
            bot.send_message(call.message.chat.id, "⚠️ جاري التحديث... تعذر جلب السعر اللحظة، حاول بعد ثوانٍ.")
            
    elif call.data == "strategy_settings":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ **إعدادات استراتيجية IRS GOLD:**\n- الزوج: الذهب (XAUUSD)\n- الأوامر: Buy-Stop & Sell-Stop\n- التنبيهات: مفعلة آلياً في الخلفية.")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **تم تفعيل المحرك بالكامل!** سيرسل لك البوت إشعارات الأوامر المعلقة تلقائياً عند أي حركة قوية.")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Bot is polling with Active IRS GOLD Alerts...")
    bot.infinity_polling()
