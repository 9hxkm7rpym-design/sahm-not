import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات سلطان (النسخة المنضبطة) ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "البوت شغال بنظام إدارة الصفقات!"
def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']
sent_trades = {} # قاموس لتخزين آخر حالة لكل سهم

def get_market_opportunities():
    for t in WATCHLIST:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            data = r['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame(data).ffill()
            p = round(df['close'].iloc[-1], 2)

            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            rsi_val = round(df['rsi'].iloc[-1])
            atr_val = df['atr'].iloc[-1]

            # التحقق من الصفقات المفتوحة ومنع التعارض
            if t in sent_trades:
                last_trade = sent_trades[t]
                # إذا السعر ضرب الوقف، نرسل تنبيه خروج ونمسح التوصية
                if (last_trade['type'] == "CALL 🟢" and p < last_trade['stop']) or \
                   (last_trade['type'] == "PUT 🔴" and p > last_trade['stop']):
                    bot.send_message(CHAT_ID, f"⚠️ **تنبيه خروج من {t}**\nالسعر تجاوز مستوى الوقف المحدد سابقاً. التزم بالحماية 🛑")
                    del sent_trades[t]
                    continue
                # إذا السعر لم يتغير كثيراً، لا نكرر الرسالة
                if abs(p - last_trade['entry']) / last_trade['entry'] < 0.01:
                    continue

            # نظام الصيد
            status = "CALL 🟢" if rsi_val < 45 else "PUT 🔴"
            stop = round(p - (atr_val * 1.5), 2) if "CALL" in status else round(p + (atr_val * 1.5), 2)
            h1 = round(p + (atr_val * 2), 2) if "CALL" in status else round(p - (atr_val * 2), 2)

            # تخزين الصفقة لمنع التكرار
            sent_trades[t] = {'type': status, 'entry': p, 'stop': stop}

            msg = (f"🤖 **تحديث من البوت الآلي**\n"
                   f"📊 إشارة تداول: {t}\n"
                   f"💰 السعر الحالي: `${p}`\n"
                   f"----------------------------------\n"
                   f"الاتجاه: {status}\n"
                   f"⚙️ **خطة العمل:**\n"
                   f"🔷 دخول: `{p}`\n"
                   f"🛑 وقف الخسارة: `{stop}`\n"
                   f"🎯 الهدف: `{h1}`\n\n"
                   f"💡 *ملاحظة: البوت لن يكرر التوصية إذا لم يتغير السعر بشكل ملحوظ.*")
            
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            time.sleep(2)
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    while True:
        get_market_opportunities()
        time.sleep(600)
