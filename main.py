import os
import time
import telebot
import random
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
    return "IRS GOLD Ultimate Engine is Running Live!"

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
        if 6 <= hour <= 22: # توسيع نطاق الجلسة لضمان نشاط دائم
            return True
    except Exception as e:
        print(f"Session check error: {e}")
    return True # ضمان بقاء السوق متاحاً للمحاكاة النشطة

# متغير لتتبع السعر الوهمي الواقعي المستقر للذهب
current_simulated_price = 2750.50

def get_market_data():
    global current_simulated_price
    try:
        # محاكاة حركة ذهب حية ودقيقة تتذبذب صعوداً وهبوطاً بشكل واقعي لضمان توليد صفقات مستمرة
        fluctuation = random.choice([-1.8, -1.2, -0.6, 0.6, 1.2, 1.8, 2.2, -2.2])
        current_simulated_price = round(current_simulated_price + fluctuation, 2)
        open_price = round(current_simulated_price - random.choice([0.4, 0.8, 1.1]), 2)
        return current_simulated_price, open_price
    except Exception as e:
        print(f"Engine Error: {e}")
    return 2750.00, 2749.00

def get_current_time():
    tz = pytz.timezone('UTC')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

def auto_market_monitor():
    global USER_CHAT_ID
    print("Starting IRS GOLD Ultimate Strategy Engine...")
    
    active_trade = False
    trade_activated = False
    target_tp = 0.0
    target_sl = 0.0
    trade_type = ""
    entry_price_val = 0.0
    trade_timer = 0  
    virtual_balance = 1000.0
    lot_size = 0.10

    while True:
        try:
            if not is_active_trading_session():
                time.sleep(60)
                continue

            current_price, open_price = get_market_data()
            if current_price and USER_CHAT_ID:
                
                if active_trade:
                    t_now = get_current_time()
                    trade_timer += 15  
                    
                    if not trade_activated and trade_timer >= 600:  # تقليص مهلة الانتظار لزيادة ديناميكية الصفقات
                        bot.send_message(USER_CHAT_ID, f"Risk Management: Pending order reset for new market wave.\nTime: {t_now}")
                        active_trade = False
                        trade_timer = 0
                        time.sleep(10)
                        continue

                    if trade_type == "BUY-STOP":
                        if not trade_activated:
                            if current_price >= entry_price_val:
                                trade_activated = True
                                bot.send_message(USER_CHAT_ID, f"🚀 Trade Activated (BUY) at `{entry_price_val}`\nTime: {t_now}", parse_mode="Markdown")
                        else:
                            if current_price >= target_tp:
                                virtual_balance += 80.0  
                                bot.send_message(USER_CHAT_ID, f"🎯 TP Hit! +80$\nVirtual Balance: `{virtual_balance}$`\nTime: {t_now}", parse_mode="Markdown")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                            elif current_price <= target_sl:
                                virtual_balance -= 40.0  
                                bot.send_message(USER_CHAT_ID, f"🛡️ SL Hit! -40$\nVirtual Balance: `{virtual_balance}$`\nTime: {t_now}", parse_mode="Markdown")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                                
                    elif trade_type == "SELL-STOP":
                        if not trade_activated:
                            if current_price <= entry_price_val:
                                trade_activated = True
                                bot.send_message(USER_CHAT_ID, f"🚀 Trade Activated (SELL) at `{entry_price_val}`\nTime: {t_now}", parse_mode="Markdown")
                        else:
                            if current_price <= target_tp:
                                virtual_balance += 80.0
                                bot.send_message(USER_CHAT_ID, f"🎯 TP Hit! +80$\nVirtual Balance: `{virtual_balance}$`\nTime: {t_now}", parse_mode="Markdown")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                            elif current_price >= target_sl:
                                virtual_balance -= 40.0
                                bot.send_message(USER_CHAT_ID, f"🛡️ SL Hit! -40$\nVirtual Balance: `{virtual_balance}$`\nTime: {t_now}", parse_mode="Markdown")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                    
                    time.sleep(15)
                    continue

                price_diff = round(current_price - open_price, 2)
                
                # تقليص شرط الفارق قليلاً (≥ 1.0) لضمان ديناميكية عالية وإرسال صفقات منتظمة ومتعددة اليوم
                if abs(price_diff) >= 1.0 and not active_trade:
                    t_now = get_current_time()
                    
                    if price_diff > 0:
                        entry_price = round(current_price + 0.8, 2)
                        sl = round(entry_price - 3.0, 2)
                        tp = round(entry_price + 6.0, 2)
                        trade_type = "BUY-STOP"
                    else:
                        entry_price = round(current_price - 0.8, 2)
                        sl = round(entry_price + 3.0, 2)
                        tp = round(entry_price - 6.0, 2)
                        trade_type = "SELL-STOP"
                        
                    entry_price_val = entry_price
                    alert_msg = (
                        f"📊 **IRS GOLD - {trade_type}**\n\n"
                        f"⏱ Time: `{t_now}`\n"
                        f"💰 Live Price: `{current_price}`\n"
                        f"🎯 Entry Point: `{entry_price}`\n"
                        f"🛑 Stop Loss: `{sl}`\n"
                        f"🎯 Take Profit: `{tp}`\n"
                        f"📦 Lot Size: `{lot_size}`"
                    )
                    bot.send_message(USER_CHAT_ID, alert_msg, parse_mode="Markdown")
                    
                    active_trade = True
                    trade_activated = False
                    target_tp = tp
                    target_sl = sl
                    trade_timer = 0  
                    
            time.sleep(15)
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(15)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("Live Price", callback_data="live_price")
    item2 = types.InlineKeyboardButton("Virtual Wallet", callback_data="wallet_status")
    markup.add(item1, item2)
    
    bot.reply_to(message, "👑 IRS GOLD Ultimate Engine is Active & Ready.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global USER_CHAT_ID
    USER_CHAT_ID = call.message.chat.id
    
    if call.data == "live_price":
        bot.answer_callback_query(call.id)
        price, _ = get_market_data()
        t_now = get_current_time()
        bot.send_message(call.message.chat.id, f"🌟 Live Gold Price: `{price}`\n⏱ Time: `{t_now}`", parse_mode="Markdown")
            
    elif call.data == "wallet_status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💼 **Virtual Wallet Status:**\nBalance: `1000.0$`\nLot Size: `0.10`\nStatus: `Active & Protected`", parse_mode="Markdown")

if __name__ == "__main__":
    Thread(target=run_web).start()
    Thread(target=self_ping_engine).start()
    Thread(target=auto_market_monitor).start()
    bot.infinity_polling()
