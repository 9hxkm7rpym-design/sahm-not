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
def home(): return "رادار سلطان: التحليل الشامل شغال!"
def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']
sent_trades = {} 

def get_safe_strike(current_price, trade_type):
    strike = round(current_price * 2) / 2
    if "CALL" in trade_type and strike <= current_price: strike += 0.5
    if "PUT" in trade_type and strike >= current_price: strike -= 0.5
    return strike

def get_market_opportunities():
    for t in WATCHLIST:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            data = r['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame(data).ffill()
            
            p = round(df['close'].iloc[-1], 2)
            high_20 = df['high'].tail(20).max()
            low_20 = df['low'].tail(20).min()

            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
            rsi_val = round(df['rsi'].iloc[-1])
            ema_val = df['ema9'].iloc[-1]
            atr_val = df['atr'].iloc[-1]

            # --- منطق تحديد الفرصة والتحليل ---
            status = "CALL 🟢" if rsi_val < 50 else "PUT 🔴"
            score = 20
            analysis_text = []

            # تحليل الدعم والمقاومة والسيولة
            if p <= low_20 * 1.002: 
                score += 30
                analysis_text.append("ارتداد من دعم")
            if p >= high_20 * 0.998:
                score += 30
                analysis_text.append("رفض من مقاومة")
            if vol_ratio > 1.5:
                score += 30
                analysis_text.append(f"سيولة انفجارية ({vol_ratio}x)")
            if (status == "CALL 🟢" and p > ema_val) or (status == "PUT 🔴" and p < ema_val):
                score += 20
                analysis_text.append("تأكيد اتجاه")

            # تصنيف درجة الثقة
            if score >= 80: confidence = "عالية جداً 🔥"
            elif score >= 55: confidence = "متوسطة ✅"
            else: confidence = "ضعيفة (مخاطرة) ⚠️"

            # منع التكرار وإدارة الوقف
            if t in sent_trades:
                last = sent_trades[t]
                if abs(p - last['entry']) / last['entry'] < 0.005: continue 
                if (last['type'] == "CALL 🟢" and p < last['stop']) or (last['type'] == "PUT 🔴" and p > last['stop']):
                    bot.send_message(CHAT_ID, f"🛑 **تنبيه خروج من {t}**\nالسعر تجاوز الوقف. احمِ محفظتك!")
                    del sent_trades[t]
                    continue

            stop = round(p - (atr_val * 1.5), 2) if "CALL" in status else round(p + (atr_val * 1.5), 2)
            h1 = round(p + (atr_val * 2.5), 2) if "CALL" in status else round(p - (atr_val * 2.5), 2)
            safe_strike = get_safe_strike(p, status)
            sent_trades[t] = {'type': status, 'entry': p, 'stop': stop}

            # --- الرسالة النهائية (الجامدة) ---
            msg = (f"🚀 **فرصة مكتشفة: {t}**\n"
                   f"----------------------------------\n"
                   f"🎯 **ثقة الصفقة: {confidence}**\n"
                   f"🧐 **التحليل:** {', '.join(analysis_text) if analysis_text else 'مضاربة سريعة'}\n"
                   f"----------------------------------\n"
                   f"📈 الاتجاه: {status}\n"
                   f"💰 السعر: `${p}`\n\n"
                   f"⚙️ **خطة العمل:**\n"
                   f"🔷 دخول: `{p}`\n"
                   f"🛑 وقف: `{stop}`\n"
                   f"🎯 هدف: `{h1}`\n\n"
                   f"📋 **العقد:** Strike {safe_strike} | {'🟢' if 'CALL' in status else '🔴'}")
            
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
            time.sleep(2)
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    while True:
        get_market_opportunities()
        time.sleep(600)
