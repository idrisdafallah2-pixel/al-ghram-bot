import os
import telebot
import requests
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TELEGRAM_TOKEN")
TWELVE_API_KEY = "308ab9dbd5744402b637d0b65b325aea"

bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "IRS GOLD Bot is Running!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        url = f"https://api.twelvedata.com/price?symbol=XAU/USD&apikey={TWELVE_API_KEY}"
        res = requests.get(url).json()
        price = res.get("price", "Unavailable")
        bot.reply_to(message, f"IRS GOLD Live Price: {price}")
    except Exception as e:
        bot.reply_to(message, f"Error fetching price: {e}")

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    bot.infinity_polling()e(call.message.chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with live API pricing.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Live API Pro Bot is polling successfully...")
    bot.infinity_polling()e(call.message.chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with live API pricing.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Live API Pro Bot is polling successfully...")
    bot.infinity_polling()"wallet_status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with live API pricing.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Live API Pro Bot is polling successfully...")
    bot.infinity_polling()ack_query(call.id)
        bot.send_message(call.message.chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with strict single-trade logic.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("CFD Pro Bot is polling successfully...")
    bot.infinity_polling()ack_query(call.id)
        bot.send_message(call.message.chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with strict single-trade logic.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("CFD Pro Bot is polling successfully...")
    bot.infinity_polling()ack_query(call.id)
        bot.send_message(call.message.chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with strict single-trade logic.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("CFD Pro Bot is polling successfully...")
    bot.infinity_polling()chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with isolated single-trade logic.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("Momentum Pro Bot is polling successfully...")
    bot.infinity_polling()_data()
        exact_time = get_current_time_with_seconds()
        if price:
            bot.send_message(call.message.chat.id, f"CFD Gold Price: `{price}`\nTime: `{exact_time}`", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "Connecting to market feed...")
            
    elif call.data == "wallet_status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Virtual Wallet Status:\nBalance: 1000.0$\nLot Size: 0.10\nRisk Control: Active", parse_mode="Markdown")
        
    elif call.data == "start_scalping":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Bot is running smoothly with strict single-trade logic.", parse_mode="Markdown")

if __name__ == "__main__":
    t_web = Thread(target=run_web)
    t_web.start()
    
    t_ping = Thread(target=self_ping_engine)
    t_ping.start()
    
    t_monitor = Thread(target=auto_market_monitor)
    t_monitor.start()
    
    print("CFD Pro Bot is polling successfully...")
    bot.infinity_polling()
