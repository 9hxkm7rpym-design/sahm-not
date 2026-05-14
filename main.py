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
def home(): return "رادار سلطان: نسخة الفلتر الذكي شغال!"
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

            # --- التحليل الفني المعمق ---
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            df['sma20'] = ta.sma(df['close'], length=20)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
            rsi_val = round(df['rsi'].iloc[-1])
            ema_val = df['ema9'].iloc[-1]

            # نظام الصيد مع فلتر اتجاه
            status = None
            if rsi_val < 45 and p > ema_val: status = "CALL 🟢" # دخول فقط إذا السعر فوق المتوسط
            elif rsi_val > 55 and p < ema_val: status = "PUT 🔴" # دخول فقط إذا السعر تحت المتوسط

            if status:
                # حساب الثقة بناءً على "تلاقي الأدلة"
                score = 20 
                reasons = []
                if vol_ratio > 1.5: 
                    score += 40
                    reasons.append(f"🔥 سيولة انفجارية ({vol_ratio}x)")
                if rsi_val < 30 or rsi_val > 70: 
                    score += 40
                    reasons.append("🎯 تشبع حاد (فرصة ذهبية)")
                
                power = "👑 ثقة ملكية" if score >= 80 else "✅ جيدة" if score >= 50 else "⚠️ مخاطرة"

                atr_val = df['atr'].iloc[-1]
                stop = round(p - (atr_val * 1.5), 2) if "CALL" in status else round(p + (atr_val * 1.5), 2)
                h1 = round(p + (atr_val * 2), 2) if "CALL" in status else round(p - (atr_val * 2), 2)

                msg = (f"🤖 **تحديث من البوت الآلي**\n"
                       f"📊 إشارة تداول: {t}\n"
                       f"💰 السعر: `${p}` | الثقة: {score}%\n"
                       f"----------------------------------\n"
                       f"💪 القوة: {power}\n"
                       f"🧐 **السبب:** {', '.join(reasons) if reasons else 'تذبذب فني'}\n"
                       f"----------------------------------\n"
                       f"الاتجاه: {status}\n"
                       f"⚙️ **خطة العمل:**\n"
                       f"🔷 دخول: `{p}`\n"
                       f"🛑 وقف: `{stop}`\n"
                       f"🎯 هدف: `{h1}`\n\n"
                       f"💡 *نصيحة: لا تدخل أي صفقة ثقتها أقل من 60% اليوم.*")
                
                bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                time.sleep(2)
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    while True:
        get_market_opportunities()
        time.sleep(600)
