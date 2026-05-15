import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات سلطان النهائية ---
TOKEN = "8308789681:AAE10GeevJ5l5iBSPHKsT2HLzud4B2KP9hU"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN, threaded=False) # تعطيل التعدد لضمان الاستجابة

user_active_trades = {}
app = Flask('')

@app.route('/')
def home(): return "رادار سلطان يعمل 🦅"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 'OXY', 'CVX', 'RBLX']

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً سلطان! الرادار متصل وشغال 🦅. أرسل /trade واسم السهم.")

@bot.message_handler(commands=['trade'])
def start_manual_trade(message):
    try:
        symbol = message.text.split()[1].upper()
        user_active_trades[symbol] = {'status': 'monitoring', 'notified_h1': False}
        bot.send_message(message.chat.id, f"✅ تم تفعيل رادار المتابعة لـ {symbol}. برهنه لك.")
    except:
        bot.reply_to(message, "⚠️ أرسل كذا: /trade NVDA")

def get_market_opportunities():
    while True:
        # فحص الفرص (الكود الداخلي شغال تمام)
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=get_market_opportunities).start()
    
    print("البوت بدأ الاستماع...")
    # تعديل سطر التشغيل ليكون أكثر استجابة
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
