import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks
from flask import Flask
from threading import Thread
import os

# --- إعدادات سلطان (المحلل والمتابع) ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

# --- تشغيل بورت وهمي لإرضاء Render ---
app = Flask('')
@app.route('/')
def home(): return "البوت شغال بأعلى كفاءة!"
def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']
active_trades = {}

def get_expert_analysis():
    print("🔄 جاري اصطياد الفرص...")
    for t in WATCHLIST:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            data = r['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame(data).ffill()
            p = round(df['close'].iloc[-1], 2)

            # --- متابعة الأهداف المحققة ---
            if t in active_trades:
                trade = active_trades[t]
                if (trade['type'] == 'CALL' and p >= trade['t1']) or (trade['type'] == 'PUT' and p <= trade['t1']):
                    bot.send_message(CHAT_ID, f"🎯 **مبروك يا سلطان! تحقق الهدف**\n✅ سهم `{t}` ضرب المحطة الأولى عند `${trade['t1']}` 💰")
                    del active_trades[t]
                    continue

            # --- التحليل الفني المطور ---
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            df['sma20'] = ta.sma(df['close'], length=20)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            # حساب السيولة الحقيقي
            current_vol = df['volume'].iloc[-1]
            avg_vol = df['volume'].tail(20).mean()
            vol_ratio = round(current_vol / avg_vol, 1) if avg_vol > 0 else 1.0

            rsi_now = df['rsi'].iloc[-1]
            ema_now = df['ema9'].iloc[-1]
            sma_now = df['sma20'].iloc[-1]

            status = None
            if rsi_now < 35 and p > ema_now: status = 'CALL'
            elif rsi_now > 65 and p < ema_now: status = 'PUT'

            if status:
                score = 0
                if vol_ratio > 1.3: score += 35
                if (status == 'CALL' and p > sma_now) or (status == 'PUT' and p < sma_now): score += 35
                if rsi_now < 30 or rsi_now > 70: score += 30

                v_desc = "انفجارية 🔥" if vol_ratio > 2.0 else "قوية ✅" if vol_ratio > 1.2 else "ضعيفة ⚠️"
                conf_desc = "ثقة ملكية 👑" if score >= 85 else "ثقة متوسطة 👍"

                peaks, _ = find_peaks(df['high'], distance=10)
                troughs, _ = find_peaks(-df['low'], distance=10)
                resistances = sorted(df['high'].iloc[peaks].unique())
                supports = sorted(df['low'].iloc[troughs].unique())

                if status == 'CALL':
                    targets = [round(r, 2) for r in resistances if r > p * 1.005]
                    stop = round(p - (df['atr'].iloc[-1] * 2), 2)
                else:
                    targets = sorted([round(s, 2) for s in supports if s < p * 0.995], reverse=True)
                    stop = round(p + (df['atr'].iloc[-1] * 2), 2)

                while len(targets) < 2: targets.append(round(targets[-1] * (1.01 if status == 'CALL' else 0.99), 2) if targets else p)
                active_trades[t] = {'type': status, 't1': targets[0]}

                msg = (f"👨‍💻 **تقرير المحلل الفني الذكي**\n"
                       f"🔍 السهم: `{t}`\n"
                       f"💰 السعر: `${p}` | السيولة: {v_desc}\n"
                       f"📊 RSI: {round(rsi_now)} | فوليوم: {vol_ratio}x\n"
                       f"------------------------------\n"
                       f"💡 **القرار الفني: {conf_desc} ({score}%)**\n"
                       f"------------------------------\n"
                       f"🎯 النوع: {'🟢 CALL' if status == 'CALL' else '🔴 PUT'}\n\n"
                       f"📐 **المحطات السعرية:**\n"
                       f"🔹 دخول: `{p}` | 🔸 وقف: `{stop}`\n"
                       f"🎯 هدف 1: `{targets[0]}`\n"
                       f"🎯 هدف 2: `{targets[1]}`\n\n"
                       f"📝 **رأي المحلل:** {'السيولة تدعم الحركة بقوة' if vol_ratio > 1.3 else 'حركة هادئة حالياً'}")
                
                bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                time.sleep(2)
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    print("✅ الرادار شغال...")
    while True:
        get_expert_analysis()
        time.sleep(600)
