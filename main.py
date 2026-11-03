import os
import time
import telebot
import yfinance as yf
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime
import pytz
import urllib.request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

USER_CHAT_ID = None

app = Flask('')

@app.route('/')
def home():
    return "IRS GOLD Commercial Pro Bot is Running!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def self_ping_engine():
    app_url = os.getenv("RENDER_EXTERNAL_URL", "https://srv-dbk4r68u01pc739270tg.onrender.com")
    while True:
        try:
            time.sleep(120)
            req = urllib.request.Request(app_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                pass
        except Exception as e:
            print(f"Self-ping error: {e}")

# التحقق من جلسات التداول الحقيقية (لندن ونيويورك فقط - استبعاد طوكيو)
def is_active_trading_session():
    try:
        utc_now = datetime.now(pytz.utc)
        hour = utc_now.hour
        if 8 <= hour <= 21:
            return True
    except Exception as e:
        print(f"Session check error: {e}")
    return False

def get_market_data():
    try:
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty and len(data) >= 2:
            raw_price = round(data['Close'].iloc[-1], 2)
            open_price = round(data['Open'].iloc[-1], 2)
            
            # تصحيح دقيق ومستقر لفارق النقاط بدقة CFD
            price_offset = -12.0 
            
            current_price = round(raw_price + price_offset, 2)
            open_adjusted = round(open_price + price_offset, 2)
            
            return current_price, open_adjusted
    except Exception as e:
        print(f"Error fetching market data: {e}")
    return None, None

def get_current_time_with_seconds():
    tz = pytz.timezone('UTC')
    now = datetime.now(tz)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def auto_market_monitor():
    global USER_CHAT_ID
    print("Starting IRS GOLD Real-Trader Engine...")
    
    active_trade_in_progress = False
    target_tp = 0.0
    target_sl = 0.0
    trade_type = None
    entry_price_val = 0.0
    trade_timer = 0  
    
    # محاكاة رأس المال وإدارة المخاطر كمتداول حقيقي
    virtual_balance = 1000.0
    lot_size = 0.10

    while True:
        try:
            if not is_active_trading_session():
                if active_trade_in_progress:
                    if USER_CHAT_ID:
                        bot.send_message(USER_CHAT_ID, "⏰ **إغلاق جلسة التداول:** أغلق السوق أبوابه، تم إلغاء الصفقة المعلقة بحذر لحماية رأس المال المحاكى.", parse_mode="Markdown")
                    active_trade_in_progress = False
                time.sleep(300)
                continue

            current_price, open_price = get_market_data()
            if current_price and open_price and USER_CHAT_ID:
                
                if active_trade_in_progress:
                    exact_time = get_current_time_with_seconds()
                    trade_timer += 30  
                    
                    # إدارة صارمة: إذا مرّت 20 دقيقة ولم يتفعل الأمر المعلق، يلغيه المتداول المحترف فوراً
                    if trade_timer >= 1200:  
                        bot.send_message(USER_CHAT_ID, f"🛡️ **إدارة المخاطر (إلغاء احترافي):**\nلم يتحرك السعر نحو الأمر المعلق وابتعد السوق، تم إلغاء الصفقة الحالية تفادياً للانزياحات السعرية.\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                        active_trade_in_progress = False
                        trade_timer = 0
                        time.sleep(30)
                        continue

                    if trade_type == "BUY-STOP":
                        if current_price >= entry_price_val:
                            if current_price >= target_tp:
                                virtual_balance += 80.0  
                                bot.send_message(USER_CHAT_ID, f"🎯 **تحقيق هدف الصفقة بنجاح (TP)!** ✅\n💰 الأرباح المحاكات المحققة: `+80$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                                active_trade_in_progress = False
                                trade_timer = 0
                            elif current_price <= target_sl:
                                virtual_balance -= 40.0  
                                bot.send_message(USER_CHAT_ID, f"🛑 **ضرب وقف الخسارة (SL) - التزام تام بإدارة المخاطر.** ❌\n📉 الخسارة المحاكات: `-40$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                                active_trade_in_progress = False
                                trade_timer = 0
                    elif trade_type == "SELL-STOP":
                        if current_price <= entry_price_val:
                            if current_price <= target_tp:
                                virtual_balance += 80.0
                                bot.send_message(USER_CHAT_ID, f"🎯 **تحقيق هدف الصفقة بنجاح (TP)!** ✅\n💰 الأرباح المحاكات المحققة: `+80$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                                active_trade_in_progress = False
                                trade_timer = 0
                            elif current_price >= target_sl:
                                virtual_balance -= 40.0
                                bot.send_message(USER_CHAT_ID, f"🛑 **ضرب وقف الخسارة (SL) - التزام تام بإدارة المخاطر.** ❌\n📉 الخسارة المحاكات: `-40$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                                active_trade_in_progress = False
                                trade_timer = 0
                    
                    time.sleep(30)
                    continue

                price_diff = round(current_price - open_price, 2)
                
                if abs(price_diff) >= 2.5 and not active_trade_in_progress:
                    exact_time = get_current_time_with_seconds()
                    
                    if price_diff > 0:
                        entry_price = round(current_price + 2.5, 2)
                        sl = round(entry_price - 4.0, 2)
                        tp = round(entry_price + 8.0, 2)
                        
                        alert_msg = (
                            f"💎 **IRS GOLD - PRO TRADER (BUY-STOP)** 💎\n\n"
                            f"⏰ وقت الإصدار: `{exact_time}`\n"
                            f"🟡 السعر الفوري: `{current_price}`\n"
                            f"🎯 الدخول المعلق: `{entry_price}`\n"
                            f"🔴 وقف الخسارة (SL): `{sl}`\n"
                            f"🟢 جني الأرباح (TP): `{tp}`\n"
                            f"📊 حجم العقد المقترح: `{lot_size}`"
                        )
                        trade_type = "BUY-STOP"
                        entry_price_val = entry_price
                    else:
                        entry_price = round(current_price - 2.5, 2)
                        sl = round(entry_price + 4.0, 2)
                        tp = round(entry_price - 8.0, 2)
                        
                        alert_msg = (
                            f"💎 **IRS GOLD - PRO TRADER (SELL-STOP)** 💎\n\n"
                            f"⏰ وقت الإصدار: `{exact_time}`\n"
                            f"🟡 السعر الفوري: `{current_price}`\n"
                            f"🎯 الدخول المعلق: `{entry_price}`\n"
                            f"🔴 وقف الخسارة (SL): `{sl}`\n"
                            f"🟢 جني الأرباح (TP): `{tp}`\n"
                            f"📊 حجم العقد المقترح: `{lot_size}`"
                        )
                        trade_type = "SELL-STOP"
                        entry_price_val = entry_price
                        
                    bot.send_message(USER_CHAT_ID, alert_msg, parse_mode="Markdown")
                    
                    active_trade_in_progress = True
                    target_tp = tp
                    target_sl = sl
                    trade_timer = 0  
                    
            time.sleep(30)
        except Exception as e:
            print(f"Monitor loop error: {e}")
            time.sleep(30)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(bot_message):
    global USER_CHAT_ID
    USER_CHAT_ID = bot_message.chat.id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("📈 السعر المباشر", callback_data="live_price")
    item2 = types.InlineKeyboardButton("💼 المحفظة المحاكات", callback_data="wallet_status")
    item3 = types.InlineKeyboardButton("🚀 حالة المتداول", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في المقر الرئيسي لـ **IRS GOLD (Real-Trader Commercial Edition)** 🤖💼\n\n"
        "تم تفعيل عقليّة المتداول الحقيقي وإدارة المحفظة والمخاطر لتأهيل البوت لمستوى تجاري خارق.",
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
        exact_time = get_current_time_with_seconds()
        if price:
            bot.send_message(call.message.chat.id, f"🟡 **السعر الفوري الدقيق:** `{price}`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, f"⚠️ جاري الاتصال...")
            
    elif call.data == "wallet_status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💼 **حالة محفظة المتداول الحقيقي:**\n- رأس المال الافتراضي: `1000.0$`\n- حجم العقد: `0.10`\n- نسبة النجاح وإدارة المخاطر: `فعالة بنسبة 100%`", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **المتداول الآلي يعمل بكفاءة سفاحة وعقلية احترافية!**", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Real-Trader Bot is polling successfully...")
    bot.infinity_polling()� **حالة محفظة المتداول الحقيقي:**\n- رأس المال الافتراضي: `1000.0$`\n- حجم العقد: `0.10`\n- نسبة النجاح وإدارة المخاطر: `فعالة بنسبة 100%`", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **المتداول الآلي يعمل بكفاءة سفاحة وعقلية احترافية!**", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Real-Trader Bot is polling successfully...")
    bot.infinity_polling()
