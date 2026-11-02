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
    return "IRS GOLD Permanent Active Bot is Running!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# آلية الإيقاظ الذاتي الجذري (Self-Ping) لتجنب السكون نهائياً من داخل الكود
def self_ping_engine():
    # الحصول على رابط التطبيق تلقائياً أو استخدام الرابط الأساسي
    app_url = os.getenv("RENDER_EXTERNAL_URL", "https://srv-dbk4r68u01pc739270tg.onrender.com")
    print(f"Self-Ping Engine started for URL: {app_url}")
    while True:
        try:
            time.sleep(120) # إرسال طلب خفيف لنفسه كل دقيقتين لمنع النوم
            req = urllib.request.Request(
                app_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                print(f"Self-ping status: {response.getcode()}")
        except Exception as e:
            print(f"Self-ping background error: {e}")

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
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty and len(data) >= 2:
            raw_price = round(data['Close'].iloc[-1], 2)
            open_price = round(data['Open'].iloc[-1], 2)
            
            # معامل التصحيح الذكي الدقيق لمطابقة سعر CFD تماماً
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
    print("Starting IRS GOLD Engine with Seconds Tracking & Anti-Sleep...")
    
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
                    exact_time = get_current_time_with_seconds()
                    if trade_type == "BUY-STOP":
                        if current_price >= target_tp:
                            bot.send_message(USER_CHAT_ID, f"✅ **تم ضرب هدف الصفقة (TP)!** 🎯\n⏰ التوقيت: `{exact_time}`\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                        elif current_price <= target_sl:
                            bot.send_message(USER_CHAT_ID, f"❌ **تم ضرب وقف الخسارة (SL).**\n⏰ التوقيت: `{exact_time}`\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                    elif trade_type == "SELL-STOP":
                        if current_price <= target_tp:
                            bot.send_message(USER_CHAT_ID, f"✅ **تم ضرب هدف الصفقة (TP)!** 🎯\n⏰ التوقيت: `{exact_time}`\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                        elif current_price >= target_sl:
                            bot.send_message(USER_CHAT_ID, f"❌ **تم ضرب وقف الخسارة (SL).**\n⏰ التوقيت: `{exact_time}`\nالسعر الحالي: `{current_price}`", parse_mode="Markdown")
                            active_trade_in_progress = False
                    
                    time.sleep(30)
                    continue

                price_diff = round(current_price - open_price, 2)
                
                if abs(price_diff) >= 2.5:
                    exact_time = get_current_time_with_seconds()
                    
                    if price_diff > 0:
                        entry_price = round(current_price + 2.5, 2)
                        sl = round(entry_price - 4.0, 2)
                        tp = round(entry_price + 8.0, 2)
                        
                        alert_msg = (
                            f"💎 **IRS GOLD - BUY-STOP** 💎\n\n"
                            f"⏰ وقت الإصدار: `{exact_time}`\n"
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
                            f"⏰ وقت الإصدار: `{exact_time}`\n"
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
                    
            time.sleep(30)
        except Exception as e:
            print(f"Monitor loop error: {e}")
            time.sleep(30)

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
        "أهلاً بك يا إدريس في المقر الرئيسي لـ **IRS GOLD (Permanent Active Edition)** 🤖\n\n"
        "تم دمج محرك الإيقاظ الذاتي للحفاظ على استقرار السيرفر واستمراريته دون أي نوم أو انقطاع.",
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
            bot.send_message(call.message.chat.id, f"🟡 **السعر المباشر:** `{price}`\n⏰ التوقيت: `{exact_time}`", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, f"⚠️ جاري الاتصال...")
            
    elif call.data == "strategy_settings":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ **الإعدادات النشطة:**\n- تتبع دقيق بالثواني لإشارات السكالبينج.\n- مطابقة سعر الذهب الفوري (CFD).\n- حماية ذاتية ضد السكون.", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🚀 **النظام يعمل بأقصى كفاءة ومحمي ذاتياً ضد السكون!**", parse_mode="Markdown")

if __name__ == "__main__":
    # تشغيل سيرفر الويب
    t_web = Thread(target=run_web)
    t_web.start()
    
    # تشغيل محرك الإيقاظ الذاتي في الخلفية
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    # تشغيل مراقب السوق والإشارات
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Permanent Active Bot is polling successfully...")
    bot.infinity_polling()
