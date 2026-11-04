import os
import time
import telebot
import requests
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime
import pytz
import urllib.request

TOKEN = os.getenv("TELEGRAM_TOKEN")
TWELVE_API_KEY = "308ab9dbd5744402b637d0b65b325aea"

bot = telebot.TeleBot(TOKEN)
USER_CHAT_ID = None

app = Flask('')

@app.route('/')
def home():
    return "IRS GOLD Full Strategy Bot is Running!"

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
        url = f"https://api.twelvedata.com/price?symbol=XAU/USD&apikey={TWELVE_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "price" in data:
            current_price = float(data["price"])
            open_price = current_price - 0.50 
            return round(current_price, 2), round(open_price, 2)
        else:
            print(f"API Response Error: {data}")
    except Exception as e:
        print(f"API Exception: {e}")
    return None, None

def get_current_time():
    tz = pytz.timezone('UTC')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

def auto_market_monitor():
    global USER_CHAT_ID
    print("Starting IRS GOLD Full Strategy Engine...")
    
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
                if active_trade and USER_CHAT_ID:
                    bot.send_message(USER_CHAT_ID, "Session Closed: Pending trade cancelled.")
                    active_trade = False
                    trade_activated = False
                time.sleep(300)
                continue

            current_price, open_price = get_market_data()
            if current_price and open_price and USER_CHAT_ID:
                
                if active_trade:
                    t_now = get_current_time()
                    trade_timer += 30  
                    
                    if not trade_activated and trade_timer >= 1200:  
                        bot.send_message(USER_CHAT_ID, f"Risk Management: Order expired after 20 mins.\nTime: {t_now}")
                        active_trade = False
                        trade_timer = 0
                        time.sleep(30)
                        continue

                    if trade_type == "BUY-STOP":
                        if not trade_activated:
                            if current_price >= entry_price_val:
                                trade_activated = True
                                bot.send_message(USER_CHAT_ID, f"Trade Activated (BUY) at {entry_price_val}\nTime: {t_now}")
                        else:
                            if current_price >= target_tp:
                                virtual_balance += 80.0  
                                bot.send_message(USER_CHAT_ID, f"TP Hit! +80$\nBalance: {virtual_balance}$\nTime: {t_now}")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                            elif current_price <= target_sl:
                                virtual_balance -= 40.0  
                                bot.send_message(USER_CHAT_ID, f"SL Hit! -40$\nBalance: {virtual_balance}$\nTime: {t_now}")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                                
                    elif trade_type == "SELL-STOP":
                        if not trade_activated:
                            if current_price <= entry_price_val:
                                trade_activated = True
                                bot.send_message(USER_CHAT_ID, f"Trade Activated (SELL) at {entry_price_val}\nTime: {t_now}")
                        else:
                            if current_price <= target_tp:
                                virtual_balance += 80.0
                                bot.send_message(USER_CHAT_ID, f"TP Hit! +80$\nBalance: {virtual_balance}$\nTime: {t_now}")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                            elif current_price >= target_sl:
                                virtual_balance -= 40.0
                                bot.send_message(USER_CHAT_ID, f"SL Hit! -40$\nBalance: {virtual_balance}$\nTime: {t_now}")
                                active_trade = False
                                trade_activated = False
                                trade_timer = 0
                    
                    time.sleep(30)
                    continue

                price_diff = round(current_price - open_price, 2)
                
                if abs(price_diff) >= 1.5 and not active_trade:
                    t_now = get_current_time()
                    
                    if price_diff > 0:
                        entry_price = round(current_price + 1.0, 2)
                        sl = round(entry_price - 3.0, 2)
                        tp = round(entry_price + 6.0, 2)
                        trade_type = "BUY-STOP"
                    else:
                        entry_price = round(current_price - 1.0, 2)
                        sl = round(entry_price + 3.0, 2)
                        tp = round(entry_price - 6.0, 2)
                        trade_type = "SELL-STOP"
                        
                    entry_price_val = entry_price
                    alert_msg = (
                        f"IRS GOLD - {trade_type}\n"
                        f"Time: {t_now}\n"
                        f"Live Price: {current_price}\n"
                        f"Entry: {entry_price}\n"
                        f"SL: {sl} | TP: {tp}\n"
                        f"Lot: {lot_size}"
                    )
                    bot.send_message(USER_CHAT_ID, alert_msg)
                    
                    active_trade = True
                    trade_activated = False
                    target_tp = tp
                    target_sl = sl
                    trade_timer = 0  
                    
            time.sleep(30)
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(30)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("Live Price", callback_data="live_price")
    item2 = types.InlineKeyboardButton("Virtual Wallet", callback_data="wallet_status")
    markup.add(item1, item2)
    
    bot.reply_to(message, "IRS GOLD Professional Strategy Bot is Active.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global USER_CHAT_ID
    USER_CHAT_ID = call.message.chat.id
    
    if call.data == "live_price":
        bot.answer_callback_query(call.id)
        price, _ = get_market_data()
        if price:
            bot.send_message(call.message.chat.id, f"Live Gold Price: {price}")
        else:
            bot.send_message(call.message.chat.id, "عذراً، جارٍ إعادة الاتصال بمزود الأسعار، حاول مرة أخرى بعد قليل.")
            
    elif call.data == "wallet_status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Virtual Wallet:\nBalance: 1000.0$\nLot Size: 0.10\nStatus: Active")

if __name__ == "__main__":
    Thread(target=run_web).start()
    Thread(target=self_ping_engine).start()
    Thread(target=auto_market_monitor).start()
    bot.infinity_polling()
