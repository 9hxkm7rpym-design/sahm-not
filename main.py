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
def home(): return "بوت سلطان: نسخة الوصف الدقيق شغال!"
def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']
sent_trades = {} 

def get_safe_strike(current_price, trade_type):
    strike = round(current_price * 2) / 2
    if trade_type == "CALL 🟢" and strike <= current_price: strike += 0.5
    if trade_type == "PUT 🔴" and strike >= current_price: strike -= 0.5
    return strike

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
            
            vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
            rsi_val = round(df['rsi'].iloc[-1])
            ema_val = df['ema9'].iloc[-1]
            atr_val = df['atr'].iloc[-1]

            if t in sent_trades:
                last = sent_trades[t]
                if (last['type'] == "CALL 🟢" and p < last['stop']) or (last['type'] == "PUT 🔴" and p > last['stop']):
                    bot.send_message(CHAT_ID, f"🛑 **خروج فني من {t}**\nالسعر كسر الوقف. برا السوق أفضل.")
                    del sent_trades[t]
                    continue
                if abs(p - last['entry']) / last['entry'] < 0.005: continue 

            status = "CALL 🟢" if rsi_val < 48 else "PUT 🔴"
            
            # حساب الثقة ووصفها
            score = 30
            if vol_ratio > 1.4: score += 35
            if (status == "CALL 🟢" and p > ema_val) or (status == "PUT 🔴" and p < ema_val): score += 20
            if rsi_val < 35 or rsi_val > 65: score += 15

            confidence_text = "عالية جداً 🔥" if score >= 80 else "عالية ✅" if score >= 60 else "متوسطة 🟡" if score >= 45 else "ضعيفة ⚠️"
            vol_text = "انفجارية 🚀" if vol_ratio > 2.0 else "عالية 📈" if vol_ratio > 1.4 else "متوسطة ⚖️" if vol_ratio > 0.8 else "ضعيفة 📉"

            stop = round(p - (atr_val * 1.5), 2) if "CALL" in status else round(p + (atr_val * 1.5), 2)
            h1 = round(p + (atr_val * 2.5), 2) if "CALL" in status else round(p - (atr_val * 2.5), 2)
            safe_strike = get_safe_strike(p, status)

            sent_trades[t] = {'type': status, 'entry': p, 'stop': stop}

            msg = (f"🤖 **إشارة تداول من رادارك**\n"
                   f"📊 السهم: **{t}**\n"
                   f"💰 السعر: `${p}`\n"
                   f"----------------------------------\n"
                   f"🎯 **درجة الثقة: {confidence_text}**\n"
                   f"🌊 **السيولة: {vol_text}**\n"
                   f"----------------------------------\n"
                   f"📈 الاتجاه: {status}\n\n"
                   f"⚙️ **خطة العمل:**\n"
                   f"🔷 دخول: `{p}`\n"
                   f"🛑 وقف: `{stop}`\n"
                   f"🎯 هدف: `{h1}`\n\n"
                   f"📋 **العقد المقترح:**\n"
                   f"Strike: **{safe_strike}** | {'🟢' if 'CALL' in status else '🔴'}\n"
                   f"----------------------------------\n"
                   f"💡 *نصيحة: ركز على صفقات الثقة العالية فقط.*")
            
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            time.sleep(2)
        except Exception as e: print(f"Error in {t}: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    while True:
        get_market_opportunities()
        time.sleep(600)
