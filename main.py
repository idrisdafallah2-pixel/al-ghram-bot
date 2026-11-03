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
    return "IRS GOLD XChief Precise Bot is Running!"

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
            
            # تعديل معامل التصحيح لضبط الـ 4 نقاط بدقة متناهية مع XChief
            # إذا كان السعر أعلى بـ 4 نقاط، نقوم بزيادة قيمة الخصم بمقدار 0.40 (أو تعديل الرقم حسب المنصة)
            price_offset = -12.40 
            
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
    print("Starting IRS GOLD XChief Precise Engine...")
    
    active_trade_in_progress = False
    target_tp = 0.0
    target_sl = 0.0
    trade_type = None
    entry_price_val = 0.0
    trade_timer = 0  
    
    virtual_balance = 1000.0
    lot_size = 0.10

    while True:
        try:
            if not is_active_trading_session():
                if active_trade_in_progress:
                    if USER_CHAT_ID:
                        bot.send_message(USER_CHAT_ID, "⏰ **إغلاق جلسة التداول:** تم إلغاء الصفقة المعلقة تلقائياً لحماية رأس المال مع نهاية جلسات السيولة.", parse_mode="Markdown")
                    active_trade_in_progress = False
                time.sleep(300)
                continue

            current_price, open_price = get_market_data()
            if current_price and open_price and USER_CHAT_ID:
                
                if active_trade_in_progress:
                    exact_time = get_current_time_with_seconds()
                    trade_timer += 30  
                    
                    if trade_timer >= 1200:  
                        bot.send_message(USER_CHAT_ID, f"🛡️ **إدارة المخاطر (إلغاء احترافي):**\nلم يتم تفعيل الأمر المعلق وابتعد السعر عنه بعد 20 دقيقة، تم إلغاء الصفقة.\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                        active_trade_in_progress = False
                        trade_timer = 0
                        time.sleep(30)
                        continue

                    if trade_type == "BUY-STOP":
                        if current_price >= entry_price_val:
                            if current_price >= target_tp:
                                virtual_balance += 80.0  
                                bot.send_message(USER_CHAT_ID, f"🎯 **تحقيق هدف الصفقة بنجاح (TP)!** ✅\n💰 الربح المحاكى: `+80$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                                active_trade_in_progress = False
                                trade_timer = 0
                            elif current_price <= target_sl:
                                virtual_balance -= 40.0  
                                bot.send_message(USER_CHAT_ID, f"🛑 **ضرب وقف الخسارة (SL).** ❌\n📉 الخسارة المحاكات: `-40$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                                active_trade_in_progress = False
                                trade_timer = 0
                    elif trade_type == "SELL-STOP":
                        if current_price <= entry_price_val:
                            if current_price <= target_tp:
                                virtual_balance += 80.0
                                bot.send_message(USER_CHAT_ID, f"🎯 **تحقيق هدف الصفقة بنجاح (TP)!** ✅\n💰 الربح المحاكى: `+80$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
                                active_trade_in_progress = False
                                trade_timer = 0
                            elif current_price >= target_sl:
                                virtual_balance -= 40.0
                                bot.send_message(USER_CHAT_ID, f"🛑 **ضرب وقف الخسارة (SL).** ❌\n📉 الخسارة المحاكات: `-40$`\n💼 الرصيد الافتراضي المحدث: `{virtual_balance}$`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
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
                            f"💎 **IRS GOLD - XCHIEF PRECISE (BUY-STOP)** 💎\n\n"
                            f"⏰ وقت الإصدار: `{exact_time}`\n"
                            f"🟡 السعر الفوري (منصة): `{current_price}`\n"
                            f"🎯 الدخول المعلق: `{entry_price}`\n"
                            f"🔴 وقف الخسارة (SL): `{sl}`\n"
                            f"🟢 جني الأرباح (TP): `{tp}`\n"
                            f"📊 حجم العقد: `{lot_size}`"
                        )
                        trade_type = "BUY-STOP"
                        entry_price_val = entry_price
                    else:
                        entry_price = round(current_price - 2.5, 2)
                        sl = round(entry_price + 4.0, 2)
                        tp = round(entry_price - 8.0, 2)
                        
                        alert_msg = (
                            f"💎 **IRS GOLD - XCHIEF PRECISE (SELL-STOP)** 💎\n\n"
                            f"⏰ وقت الإصدار: `{exact_time}`\n"
                            f"🟡 السعر الفوري (منصة): `{current_price}`\n"
                            f"🎯 الدخول المعلق: `{entry_price}`\n"
                            f"🔴 وقف الخسارة (SL): `{sl}`\n"
                            f"🟢 جني الأرباح (TP): `{tp}`\n"
                            f"📊 حجم العقد: `{lot_size}`"
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
    item2 = types.InlineKeyboardButton("💼 المحفظة الافتراضية", callback_data="wallet_status")
    item3 = types.InlineKeyboardButton("🚀 حالة النظام", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في المقر الرئيسي لـ **IRS GOLD (XChief Precise Edition)** 🤖💼\n\n"
        "تم ضبط معيار فروق الأسعار ليتطابق بدقة تامة مع منصة XChief.",
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
            bot.send_message(call.message.chat.id, f"🟡 **سعر الذهب (مطابق XChief):** `{price}`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, f"⚠️ جاري الاتصال بالبث المباشر...")
            
    elif call.data == "wallet_status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💼 **حالة محفظة المتداول الحقيقي:**\n- رأس المال: `1000.0$`\n- حجم العقد: `0.10`\n- إدارة المخاطر: `نشطة بنسبة 100%`", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **البوت يعمل بجهوزية تامة ودقة أسعار محسنة!**", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping =Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("XChief Precise Bot is polling successfully...")
    bot.infinity_polling() Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("XChief Pro Bot is polling successfully...")
    bot.infinity_polling()
