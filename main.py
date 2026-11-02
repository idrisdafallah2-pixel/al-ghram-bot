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

USER_CHAT_ID = None

app = Flask('')

@app.route('/')
def home():
    return "AL-GHRAM TRADING BOT - Stable Gold Engine is Active!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def is_active_trading_session():
    try:
        utc_now = datetime.now(pytz.utc)
        hour = utc_now.hour
        if 8 <= hour <= 20:
            return True
    except Exception as e:
        print(f"Session check error: {e}")
    return True

def get_market_data():
    try:
        # العودة إلى الرمز الأساسي المستقر جداً GC=F لضمان عدم توقف الاتصال
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="5m")
        if not data.empty and len(data) >= 2:
            raw_price = round(data['Close'].iloc[-1], 2)
            open_price = round(data['Open'].iloc[-1], 2)
            
            # فارق السعر اللحظي الثابت لضمان المطابقة مع منصتك
            price_offset = -13.0 
            
            current_price = round(raw_price + price_offset, 2)
            open_adjusted = round(open_price + price_offset, 2)
            
            return current_price, open_adjusted
    except Exception as e:
        print(f"Error fetching market data: {e}")
    return None, None

def auto_market_monitor():
    global USER_CHAT_ID
    print("Starting Stable IRS GOLD Engine...")
    
    active_trade_in_progress = False
    target_tp = 0.0
    target_sl = 0.0
    trade_type = None

    while True:
        try:
            if not is_active_trading_session():
                time.sleep(300)
                continue

            current_price, open_price = get_market_data()
            if current_price and open_price and USER_CHAT_ID:
                
                if active_trade_in_progress:
                    if trade_type == "BUY-STOP":
                        if current_price >= target_tp:
                            bot.send_message(USER_CHAT_ID, f"✅ **تم ضرب هدف الصفقة (TP)!** 🎯\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                        elif current_price <= target_sl:
                            bot.send_message(USER_CHAT_ID, f"❌ **تم ضرب وقف الخسارة (SL).**\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                    elif trade_type == "SELL-STOP":
                        if current_price <= target_tp:
                            bot.send_message(USER_CHAT_ID, f"✅ **تم ضرب هدف الصفقة (TP)!** 🎯\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                        elif current_price >= target_sl:
                            bot.send_message(USER_CHAT_ID, f"❌ **تم ضرب وقف الخسارة (SL).**\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                    
                    time.sleep(60)
                    continue

                price_diff = round(current_price - open_price, 2)
                
                if abs(price_diff) >= 2.5:
                    if price_diff > 0:
                        entry_price = round(current_price + 2.5, 2)
                        sl = round(entry_price - 4.0, 2)
                        tp = round(entry_price + 8.0, 2)
                        
                        alert_msg = (
                            f"💎 **IRS GOLD - BUY-STOP** 💎\n\n"
                            f"🟡 السعر الحالي: `{current_price}`\n"
                            f"🎯 الدخول المعلق: `{entry_price}`\n"
                            f"🔴 وقف الخسارة (SL): `{sl}`\n"
                            f"🟢 جني الأرباح (TP): `{tp}`"
                        )
                        trade_type = "BUY-STOP"
                    else:
                        entry_price = round(current_price - 2.5, 2)
                        sl = round(entry_price + 4.0, 2)
                        tp = round(entry_price - 8.0, 2)
                        
                        alert_msg = (
                            f"💎 **IRS GOLD - SELL-STOP** 💎\n\n"
                            f"🟡 السعر الحالي: `{current_price}`\n"
                            f"🎯 الدخول المعلق: `{entry_price}`\n"
                            f"🔴 وقف الخسارة (SL): `{sl}`\n"
                            f"🟢 جني الأرباح (TP): `{tp}`"
                        )
                        trade_type = "SELL-STOP"
                        
                    bot.send_message(USER_CHAT_ID, alert_msg, parse_mode="Markdown")
                    
                    active_trade_in_progress = True
                    target_tp = tp
                    target_sl = sl
                    
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
    item3 = types.InlineKeyboardButton("🚀 تشغيل النظام", callback_data="start_scalping")
    markup.add(item1, item2, item3)
    
    bot.reply_to(
        bot_message, 
        "أهلاً بك يا إدريس في المقر الرئيسي لـ **IRS GOLD (Stable Engine)** 🤖\n\n"
        "تم استقرار الاتصال بالكامل مع تصفية الرسائل (السعر، الدخول، الاستوب، الهدف) والتتابع النظامي.",
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
            bot.send_message(call.message.chat.id, f"🟡 **سعر الذهب المباشر:** `{price}`")
        else:
            bot.send_message(call.message.chat.id, f"⚠️ جاري الاتصال...")
            
    elif call.data == "strategy_settings":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ **الإعدادات النشطة:**\n- الاستقرار: اتصال مستقر ودائم 24/7.\n- الأركان: نقي (السعر، الدخول، الاستوب، الهدف).\n- التتابع: صفقة واحدة تتبعها الأخرى.")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **النظام يعمل بأقصى ثبات وسرعة استجابة!**")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Stable Bot is polling successfully...")
    bot.infinity_polling()
