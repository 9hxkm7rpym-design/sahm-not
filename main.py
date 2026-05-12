import telebot
import requests
import pandas as pd
import pandas_ta as ta
import time
from flask import Flask
from threading import Thread
import os

# تشغيل سيرفر ويب صغير
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# بياناتك الثابتة
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

WATCHLIST = ['AAPL', 'SPY', 'MSFT', 'AMZN', 'NVDA', 'UNH', 'LLY', 'OXY']

def get_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers).json()
        c = pd.Series(r['chart']['result'][0]['indicators']['quote'][0]['close'])
        v = pd.Series(r['chart']['result'][0]['indicators']['quote'][0]['volume'])
        p = c.iloc[-1]
        rsi = ta.rsi(c, length=14).iloc[-1]
        sma = ta.sma(c, length=50).iloc[-1]
        liq = "عالية 🔥" if v.iloc[-1] > v.tail(10).mean() else "ضعيفة ⚠️"
        return round(p, 2), round(rsi, 2), round(sma, 2), liq
    except: return None, None, None, None

def check_and_send():
    for t in WATCHLIST:
        p, r, s, l = get_data(t)
        if p and r:
            trend = "🟢 صاعد" if p > s else "🔴 هابط"
            if (r < 32 and p > (s * 0.98)) or (r > 68):
                sig = "كول (CALL)" if r < 32 else "بوت (PUT)"
                emo = "🟢" if r < 32 else "🔴"
                stk = round(p) + 1 if r < 32 else round(p) - 1
                msg = (f"🤖 **رسالة من البوت الآلي** 🤖\n"
                       f"📊 إشارة تداول {t}\n"
                       f"💰 السعر: ${p} | RSI: {r}\n"
                       f"📊 السيولة: {l}\n"
                       f"-------------------\n"
                       f"الاتجاه: {trend}\n"
                       f"{emo} النوع: {sig} | Strike: {stk}\n"
                       f"🎯 الأهداف: +1% | +3%\n"
                       f"🛑 الوقف: -1%")
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.send_message(CHAT_ID, "✅ تم التحديث بنجاح يا سلطان.. الرادار شغال.")
    while True:
        check_and_send()
        time.sleep(300)
