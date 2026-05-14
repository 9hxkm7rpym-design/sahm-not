import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات سلطان الخاصة ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار سلطان شغال بنفس التنسيق المفضل!"
def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']

def get_market_opportunities():
    for t in WATCHLIST:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            data = r['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame(data).ffill()
            p = round(df['close'].iloc[-1], 2)

            # --- الحسابات الفنية ---
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            df['sma20'] = ta.sma(df['close'], length=20)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
            rsi_val = round(df['rsi'].iloc[-1])
            sma_val = round(df['sma20'].iloc[-1], 2)
            ema_val = df['ema9'].iloc[-1]

            # نظام الصيد (يرسل كل الفرص)
            status = "CALL 🟢" if rsi_val < 50 else "PUT 🔴"
            
            # حساب الثقة والتحليل
            score = 30
            analysis_notes = []
            if vol_ratio > 1.3: 
                score += 30
                analysis_notes.append(f"🔥 سيولة عالية ({vol_ratio}x)")
            if (status == "CALL 🟢" and p > ema_val) or (status == "PUT 🔴" and p < ema_val):
                score += 20
                analysis_notes.append("📈 تأكيد الاتجاه")
            if rsi_val < 30 or rsi_val > 70:
                score += 20
                analysis_notes.append("🎯 تشبع حاد (انعكاس)")

            atr_val = df['atr'].iloc[-1]
            stop = round(p - (atr_val * 2), 2) if "CALL" in status else round(p + (atr_val * 2), 2)
            h1 = round(p + (atr_val * 2.5), 2) if "CALL" in status else round(p - (atr_val * 2.5), 2)
            h2 = round(p + (atr_val * 4), 2) if "CALL" in status else round(p - (atr_val * 4), 2)

            # --- التنسيق المفضل لـ سلطان ---
            msg = (f"🤖 **رسالة من البوت الآلي**\n"
                   f"📊 إشارة تداول: {t}\n"
                   f"💰 السعر الحالي: `${p}`\n"
                   f"📈 RSI: {rsi_val} | SMA: {sma_val}\n"
                   f"----------------------------------\n"
                   f"📊 **درجة الثقة: {score}%**\n"
                   f"🧐 **لماذا؟** {', '.join(analysis_notes) if analysis_notes else 'حركة مضاربية'}\n"
                   f"----------------------------------\n"
                   f"الاتجاه: {status}\n"
                   f"الصلاحية: 🕒 Intraday\n\n"
                   f"⚙️ **خطة التنفيذ (محطات الشارت):**\n"
                   f"🔷 منطقة الدخول: `{p}`\n"
                   f"🔷 مستوى الوقف: `{stop}`\n"
                   f"🎯 هدف 1: `{h1}`\n"
                   f"🎯 هدف 2: `{h2}`\n\n"
                   f"📋 **العقد المقترح:**\n"
                   f"Strike: {round(h1)} | {'🟢' if 'CALL' in status else '🔴'}")
            
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            time.sleep(2)
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    while True:
        get_market_opportunities()
        time.sleep(600)
