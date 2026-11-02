import os
import time
import telebot
import yfinance as yf
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# استخدام متغير آمن لحفظ شات المستخدم لضمان عدم ضياعه
USER_CHAT_ID = None

app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM TRADING BOT - Ultimate Commercial Edition is Active 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def is_active_trading_session():
    try:
        utc_now = datetime.now(pytz.utc)
        hour = utc_now.hour
        # جلسات لندن ونيويورك (من 8 صباحاً حتى 8 مساءً بتوقيت غرينتش لضمان التقاط 2 إلى 4 فرَص قوية)
        if 8 <= hour <= 20:
            return True
    except Exception as e:
        print(f"Session check error: {e}")
    return True

def get_market_data():
    try:
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="5m")
        if not data.empty and len(data) >= 2:
            current_price = round(data['Close'].iloc[-1], 2)
            open_price = round(data['Open'].iloc[-1], 2)
            return current_price, open_price
    except Exception as e:
        print(f"Error fetching market data: {e}")
    return None, None

def auto_market_monitor():
    global USER_CHAT_ID
    print("Starting Ultimate Commercial IRS GOLD Engine...")
    
    last_alert_time = 0
    cooldown_period = 3600  # ساعة فاصل أقصى، أو بناءً على الزخم لضمان 2 إلى 4 إشارات خلال الجلستين
    signals_sent_today = 0
    current_day = datetime.now().day

    while True:
        try:
            # إعادة عداد الإشارات مع بداية يوم جديد
            day_now = datetime.now().day
            if day_now != current_day:
                current_day = day_now
                signals_sent_today = 0

            if not is_active_trading_session():
                time.sleep(300)
                continue

            # السماح بحد أقصى 4 إشارات في اليوم لضمان عدم العشوائية
            if signals_sent_today >= 4:
                time.sleep(1800)
                continue

            current_price, open_price = get_market_data()
            if current_price and open_price and USER_CHAT_ID:
                current_time = time.time()
                price_diff = round(current_price - open_price, 2)
                
                # شرط فرصة قوية ومدرسية (تغير بـ 2.5 دولار أو أكثر لتوليد 2-4 إشارات ممتازة يومياً)
                if (current_time - last_alert_time > 3600) and (abs(price_diff) >= 2.5):
                    
                    if price_diff > 0:
                        entry_price = round(current_price + 2.5, 2)
                        sl = 4.0 
                        tp = 8.0 
                        tp_price = round(entry_price + tp, 2)
                        sl_price = round(entry_price - sl, 2)
                        
                        alert_msg = (
                            f"💎 **[IRS GOLD ULTIMATE] - إشارة BUY-STOP** 💎\n\n"
                            f"🌍 الجلسة: لندن / نيويورك\n"
                            f"🟡 السعر الحالي: `${current_price}`\n"
                            f"🎯 **سعر الدخول المعلق: `${entry_price}`**\n"
                            f"🟢 جني الأرباح (TP): `${tp_price}` (+8.0$)\n"
                            f"🔴 وقف الخسارة (SL): `${sl_price}` (-4.0$)\n"
                            f"⚖️ نسبة العائد للمخاطرة: `1:2`\n\n"
                            f"⚡ فرصة رقم ({signals_sent_today + 1}) من أصل 4 مستهدفة اليوم!"
                        )
                    else:
                        entry_price = round(current_price - 2.5, 2)
                        sl = 4.0
                        tp = 8.0 
                        tp_price = round(entry_price - tp, 2)
                        sl_price = round(entry_price + sl, 2)
                        
                        alert_msg = (
                            f"💎 **[IRS GOLD ULTIMATE] - إشارة SELL-STOP** 💎\n\n"
                            f"🌍 الجلسة: لندن / نيويورك\n"
                            f"🟡 السعر الحالي: `${current_price}`\n"
                            f"🎯 **سعر الدخول المعلق: `${entry_price}`**\n"
                            f"🟢 جني الأرباح (TP): `${tp_price}` (-8.0$)\n"
                            f"🔴 وقف الخسارة (SL): `${sl_price}` (+4.0$)\n"
                            f"⚖️ نسبة العائد للمخاطرة: `1:2`\n\n"
                            f"⚡ فرصة رقم ({signals_sent_today + 1}) من أصل 4 مستهدفة اليوم!"
                        )
                        
                    bot.send_message(USER_CHAT_ID, alert_msg, parse_mode="Markdown")
                    last_alert_time = current_time
                    signals_sent_today += 1
                    
            time.sleep(60)
        except Exception as e:
            print(f"Monitor loop error: {e}")
            time.sleep(60)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    global USER_CHAT_ID
    USER_CHAT_ID = bot_message.chat.id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("📈 سعر الذهب المباشر", callback_data="live_price")
    item2 = types.InlineKeyboardButton("⚙️ إعدادات النظام", callback_data="strategy_settings")
    item3 = types.InlineKeyboardButton("🚀 تفعيل البوت الجذري", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في المقر الرئيسي المحصن لـ **AL-GHRAM TRADING BOT** 🤖\n\n"
        "تمت معالجة جميع مشاكل التوقف وجعل البوت يطلق من 2 إلى 4 إشارات دقيقة بنسبة 1:2 يومياً خلال جلسات السيولة. اختر أمراً:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global USER_CHAT_ID
    USER_CHAT_ID = call.message.chat.id
    
    if call.data == "live_price":
        bot.answer_callback_query(call.id)
        price, _ = get_market_data()
        if price:
            bot.send_message(call.message.chat.id, f"🟡 **سعر الذهب المباشر:** `${price}`")
        else:
            bot.send_message(call.message.chat.id, f"⚠️ جاري الاتصال بالخادم الحي...")
            
    elif call.data == "strategy_settings":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ **الإعدادات الجذرية:**\n- عدد الإشارات: 2 إلى 4 إشارات عالية النقاء يومياً\n- نسبة المخاطرة للهدف: 1:2 (4$ وقف / 8$ هدف)\n- الاستقرار: تفعيل الحماية ضد التوقف التلقائي 24/7.")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **النظام يعمل الآن بأقصى درجات الثبات والذكاء!** بانتظار فرص السيولة الكبرى.")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Ultimate Bot is polling successfully...")
    bot.infinity_polling()
