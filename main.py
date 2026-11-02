import os
import time
import telebot
import yfinance as yf
from flask import Flask
from threading import Thread
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

USER_CHAT_ID = None

app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM TRADING BOT is live with Ultimate IRS GOLD Strategy!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def get_gold_price():
    try:
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="5m") # الاعتماد على فريم 5 دقائق لدقة السكالبينج
        if not data.empty:
            current_price = round(data['Close'].iloc[-1], 2)
            open_price = round(data['Open'].iloc[-1], 2)
            return current_price, open_price
    except Exception as e:
        print(f"Error fetching price: {e}")
    return None, None

def auto_market_monitor():
    global USER_CHAT_ID
    print("Starting Ultimate IRS GOLD Strategy Monitor...")
    
    last_alert_time = 0
    cooldown_period = 600 # منع إرسال إشارات متكررة قبل مرور 10 دقائق لضمان قوة الفرصة
    
    while True:
        try:
            current_price, open_price = get_gold_price()
            if current_price and open_price and USER_CHAT_ID:
                current_time = time.time()
                
                # فحص الزخم السعري للشمعة الحالية (الفرق بين الاغلاق والافتتاح)
                candle_diff = round(current_price - open_price, 2)
                
                # شرط الفرصة القوية: تحرك معتبر بـ 3 دولار أو أكثر في الشمعة الحالية
                if (current_time - last_alert_time > cooldown_period) and abs(candle_diff) >= 3.0:
                    
                    if candle_diff > 0:
                        # زخم صاعد قوي: نقترح أمر Buy-Stop معلق فوق السعر الحالي بمسافة 3 دولار
                        entry_price = round(current_price + 3.0, 2)
                        tp = round(entry_price + 7.0, 2) # هدف قوي (7 دولار)
                        sl = round(entry_price - 4.0, 2) # وقف خسارة محكم (4 دولار)
                        
                        alert_msg = (
                            f"🔥 **استراتيجية IRS GOLD القوية (BUY-STOP)** 🔥\n\n"
                            f"🟡 سعر السوق الحالي: `${current_price}`\n"
                            f"🎯 **سعر الدخول المعلق: `${entry_price}`**\n"
                            f"🟢 جني الأرباح (TP): `${tp}`\n"
                            f"🔴 وقف الخسارة (SL): `${sl}`\n\n"
                            f"⚡ الزخم شرائي قوي، تم رصد انطلاقة معتبرة!"
                        )
                    else:
                        # زخم هابط قوي: نقترح أمر Sell-Stop معلق تحت السعر الحالي بمسافة 3 دولار
                        entry_price = round(current_price - 3.0, 2)
                        tp = round(entry_price - 7.0, 2)
                        sl = round(entry_price + 4.0, 2)
                        
                        alert_msg = (
                            f"🔥 **استراتيجية IRS GOLD القوية (SELL-STOP)** 🔥\n\n"
                            f"🟡 سعر السوق الحالي: `${current_price}`\n"
                            f"🎯 **سعر الدخول المعلق: `${entry_price}`**\n"
                            f"🟢 جني الأرباح (TP): `${tp}`\n"
                            f"🔴 وقف الخسارة (SL): `${sl}`\n\n"
                            f"⚡ الزخم بيعي قوي، تم رصد هبوط معتبر!"
                        )
                        
                    bot.send_message(USER_CHAT_ID, alert_msg, parse_mode="Markdown")
                    last_alert_time = current_time
                    
            time.sleep(60)
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(60)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    global USER_CHAT_ID
    USER_CHAT_ID = bot_message.chat.id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("📈 سعر الذهب المباشر", callback_data="live_price")
    item2 = types.InlineKeyboardButton("⚙️ إعدادات الاستراتيجية", callback_data="strategy_settings")
    item3 = types.InlineKeyboardButton("🚀 تفعيل النظام القوي", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في القمة مع **AL-GHRAM TRADING BOT** 🤖\n\n"
        "تم تفعيل النسخة الأقوى لاستراتيجية **IRS GOLD** (أوامر معلقة بمسافة آمنة، أهداف، وقف خسارة، وفلترة الزخم). اختر أحد الخيارات:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global USER_CHAT_ID
    USER_CHAT_ID = call.message.chat.id
    
    if call.data == "live_price":
        bot.answer_callback_query(call.id)
        price, _ = get_gold_price()
        if price:
            bot.send_message(call.message.chat.id, f"🟡 **سعر الذهب المباشر الآن:** `${price}`")
        else:
            bot.send_message(call.message.chat.id, "⚠️ جاري التحديث... حاول بعد ثوانٍ.")
            
    elif call.data == "strategy_settings":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ **إعدادات الاستراتيجية القوية:**\n- الإطار الزمني: M5\n- مسافة الأوامر المعلقة: مدروسة بدقة\n- إدارة المخاطر: TP و SL مدمجة تلقائياً\n- التكرار: مفلترة تماماً (لا إشارات عشوائية).")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **النظام الخارق يعمل بأقصى كفاءة!** ترقب أقوى الفرص والإشارات المعلقة على تيليجرام.")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Bot is polling with Ultimate IRS GOLD Engine...")
    bot.infinity_polling()
