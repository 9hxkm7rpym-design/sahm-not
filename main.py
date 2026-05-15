import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات سلطان (نسخة الفلتر الصارم) ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار سلطان: نسخة الفلتر الصارم شغالة!"
def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']
sent_trades = {} 

def get_market_opportunities():
    for t in WATCHLIST:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            data = r['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame(data).ffill()
            
            p = round(df['close'].iloc[-1], 2)
            df['ema20'] = ta.ema(df['close'], length=20)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            ema_val = df['ema20'].iloc[-1]
            rsi_val = round(df['rsi'].iloc[-1])
            atr_val = df['atr'].iloc[-1]
            vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)

            # --- الفلتر الصارم: لا دخول عكس الاتجاه اللحظي ---
            status = None
            analysis = []
            score = 20

            if p > ema_val and rsi_val < 50: # CALL فقط إذا السعر فوق المتوسط
                status = "CALL 🟢"
                analysis.append("تأسيس فوق المتوسط")
            elif p < ema_val and rsi_val > 50: # PUT فقط إذا السعر تحت المتوسط
                status = "PUT 🔴"
                analysis.append("فشل تحت المتوسط")

            if not status: continue # تجاهل أي إشارة "عكس السير"

            # حساب الثقة
            if vol_ratio > 1.5: 
                score += 40
                analysis.append(f"سيولة عالية ({vol_ratio}x)")
            if (status == "CALL 🟢" and rsi_val < 35) or (status == "PUT 🔴" and rsi_val > 65):
                score += 30
                analysis.append("منطقة انعكاس ذهبية")

            # إدارة التكرار والوقف
            if t in sent_trades:
                last = sent_trades[t]
                if (last['type'] == "CALL 🟢" and p < last['stop']) or (last['type'] == "PUT 🔴" and p > last['stop']):
                    bot.send_message(CHAT_ID, f"🛑 **خروج من {t}**\nالسهم كسر مستوى الأمان. لا تعاند الاتجاه!")
                    del sent_trades[t]
                    continue
                if abs(p - last['entry']) / last['entry'] < 0.005: continue 

            confidence = "عالية جداً 🔥" if score >= 80 else "جيدة ✅" if score >= 55 else "ضعيفة ⚠️"
            stop = round(p - (atr_val * 1.8), 2) if "CALL" in status else round(p + (atr_val * 1.8), 2)
            h1 = round(p + (atr_val * 2.5), 2) if "CALL" in status else round(p - (atr_val * 2.5), 2)

            sent_trades[t] = {'type': status, 'entry': p, 'stop': stop}

            msg = (f"🤖 **تحليل الرادار: {t}**\n"
                   f"💰 السعر: `${p}`\n"
                   f"----------------------------------\n"
                   f"🎯 **الثقة: {confidence}**\n"
                   f"🧐 **التحليل:** {', '.join(analysis)}\n"
                   f"----------------------------------\n"
                   f"📈 الاتجاه: {status}\n\n"
                   f"⚙️ **الخطة:**\n"
                   f"🔷 دخول: `{p}` | 🛑 وقف: `{stop}`\n"
                   f"🎯 هدف: `{h1}`\n\n"
                   f"💡 *نصيحة: إذا الثقة 'ضعيفة' واليوم جمعة، خلك متفرج.*")
            
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            time.sleep(2)
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    while True:
        get_market_opportunities()
        time.sleep(600)
