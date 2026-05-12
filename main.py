import telebot
import requests
import pandas as pd
import pandas_ta as ta
import time
import os

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
            if (r < 30 and p > (s * 0.98)) or (r > 70):
                sig = "كول (CALL)" if r < 30 else "بوت (PUT)"
                emo = "🟢" if r < 30 else "🔴"
                stk = round(p) + 1 if r < 30 else round(p) - 1
                msg = (f"🤖 **رسالة من البوت الآلي** 🤖\n"
                       f"📊 إشارة تداول {t}\n"
                       f"💰 السعر: ${p} | RSI: {r}\n"
                       f"📊 السيولة: {l}\n"
                       f"-------------------\n"
                       f"الاتجاه: {trend}\n"
                       f"{emo} النوع: {sig} | Strike: {stk}")
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")

if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🚀 تم تشغيل الرادار بنجاح يا سلطان.. جاري فحص الشركات.")
    while True:
        check_and_send()
        time.sleep(300)
