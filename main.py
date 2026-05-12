import telebot
import requests
import pandas as pd
import pandas_ta as ta
import time
from flask import Flask
from threading import Thread

# تشغيل سيرفر صغير عشان Render ما يطفي البوت
app = Flask('')
@app.route('/')
def home():
    return "البوت شغال يا سلطان.. صيد موفق! 🦅"

def run_web():
    app.run(host='0.0.0.0', port=8080)

TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

# قائمة الشركات الشاملة (تكنولوجيا، طاقة، صحة)
WATCHLIST = ['AAPL', 'SPY', 'MSFT', 'AMZN', 'NVDA', 'UNH', 'LLY', 'OXY']

def get_market_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        result = response['chart']['result'][0]
        close_prices = pd.Series(result['indicators']['quote'][0]['close'])
        volumes = pd.Series(result['indicators']['quote'][0]['volume'])
        
        price = close_prices.iloc[-1]
        rsi = ta.rsi(close_prices, length=14).iloc[-1]
        sma = ta.sma(close_prices, length=50).iloc[-1]
        
        avg_vol = volumes.tail(10).mean()
        current_vol = volumes.iloc[-1]
        liquidity = "عالية 🔥" if current_vol > avg_vol else "ضعيفة ⚠️"
        
        return round(price, 2), round(rsi, 2), round(sma, 2), liquidity
    except:
        return None, None, None, None

def send_signal(ticker, price, rsi, sma, liquidity):
    trend = "🟢 صاعد" if price > sma else "🔴 هابط"
    if rsi < 32 and price > (sma * 0.97): # إشارة كول
        m_emoji, s_type, c_emoji = "📈", "كول (CALL)", "🟢"
        strike = round(price) + 1
    elif rsi > 68: # إشارة بوت
        m_emoji, s_type, c_emoji = "📉", "بوت (PUT)", "🔴"
        strike = round(price) - 1
    else: return

    msg = (f"🤖 **رسالة من البوت الآلي** 🤖\n"
           f"📊 إشارة تداول {ticker}\n"
           f"💰 السعر الحالي: ${price}\n"
           f"📈 RSI: {rsi} | SMA: {sma}\n"
           f"📊 السيولة: {liquidity}\n"
           f"-------------------\n"
           f"الاتجاه: {trend}\n"
           f"{c_emoji} النوع: {s_type}\n"
           f"🟡 درجة الثقة: متوسطة ⚡️\n\n"
           f"⚙️ **خطة التنفيذ:**\n"
           f"🔹 منطقة الدخول: {price}\n"
           f"🎯 هدف 1: {round(price * 1.01, 2)}\n"
           f"🎯 هدف 2: {round(price * 1.03, 2)}\n"
           f"🛑 مستوى الوقف: {round(price * 0.99, 2)}\n\n"
           f"📋 **العقد المقترح:**\n"
           f"{m_emoji} {s_type} | Strike: {strike}")
    bot.send_message(CHAT_ID, msg, parse_mode="Markdown")

if __name__ == "__main__":
    # تشغيل السيرفر في خلفية الكود
    t = Thread(target=run_web)
    t.start()
    
    bot.send_message(CHAT_ID, "✅ تم تشغيل رادار سلطان بنجاح.. البوت لن ينام بعد اليوم!")
    
    while True:
        for ticker in WATCHLIST:
            p, r, s, l = get_market_data(ticker)
            if p:
                send_signal(ticker, p, r, s, l)
        time.sleep(300) # فحص كل 5 دقائق
