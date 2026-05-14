import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks
from flask import Flask
from threading import Thread

# --- إعدادات سلطان الخاصة ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

# --- كود إرضاء سيرفر Render (عشان ما يعلق) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"
def run(): app.run(host='0.0.0.0', port=10000)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']
active_trades = {}

def get_expert_analysis():
    print("🔄 جاري تحليل السوق الآن يا سلطان...")
    for t in WATCHLIST:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            data = r['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame(data).ffill()
            p = round(df['close'].iloc[-1], 2)

            # متابعة الأهداف
            if t in active_trades:
                trade = active_trades[t]
                if (trade['type'] == 'CALL' and p >= trade['t1']) or (trade['type'] == 'PUT' and p <= trade['t1']):
                    bot.send_message(CHAT_ID, f"🎯 **تحقق الهدف يا سلطان!**\nسهم `{t}` وصل لهدفه: `${trade['t1']}` 💰")
                    del active_trades[t]
                    continue

            # التحليل الفني المتقدم
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            df['sma20'] = ta.sma(df['close'], length=20)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
            rsi_now = df['rsi'].iloc[-1]
            ema_now = df['ema9'].iloc[-1]
            sma_now = df['sma20'].iloc[-1]

            # تحديد الاتجاه
            trend = "جانبي ↔️"
            if p > ema_now > sma_now: trend = "صاعد قوي 🔥"
            elif p < ema_now < sma_now: trend = "هابط حاد ❄️"

            status = None
            if rsi_now < 35 and p > ema_now: status = 'CALL'
            elif rsi_now > 65 and p < ema_now: status = 'PUT'

            if status:
                score = 0
                if vol_ratio > 1.3: score += 35
                if (status == 'CALL' and p > sma_now) or (status == 'PUT' and p < sma_now): score += 35
                if rsi_now < 30 or rsi_now > 70: score += 30

                v_desc = "انفجارية ⚡" if vol_ratio > 2.0 else "قوية ✅" if vol_ratio > 1.2 else "ضعيفة ⚠️"
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

                while len(targets) < 2: targets.append(round(targets[-1] * 1.01, 2) if targets else p)
                active_trades[t] = {'type': status, 't1': targets[0]}

                msg = (f"👨‍💻 **تقرير المحلل الفني الذكي**\n"
                       f"🔍 السهم: `{t}` | الاتجاه: {trend}\n"
                       f"💰 السعر: `${p}` | السيولة: {v_desc}\n"
                       f"📊 RSI: {round(rsi_now)} | فوليوم: {vol_ratio}x\n"
                       f"------------------------------\n"
                       f"💡 **القرار الفني: {conf_desc} ({score}%)**\n"
                       f"------------------------------\n"
                       f"🎯 النوع: {'🟢 CALL' if status == 'CALL' else '🔴 PUT'}\n\n"
                       f"📐 **المحطات السعرية:**\n"
                       f"🔹 دخول: `{p}`\n"
                       f"🔸 وقف: `{stop}`\n"
                       f"🎯 هدف 1: `{targets[0]}`\n"
                       f"🎯 هدف 2: `{targets[1]}`")
                
                bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                time.sleep(2)
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run).start() # تشغيل الخادم الوهمي
    print("✅ المحلل والمتابع شغال الحين...")
    while True:
        get_expert_analysis()
        time.sleep(600)
