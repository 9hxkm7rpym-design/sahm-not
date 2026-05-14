import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks
from flask import Flask
from threading import Thread
import os

# --- إعدادات سلطان (بوت المحلل المحترف) ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

# --- فاتح البورت لضمان استقرار البوت على Render ---
app = Flask('')
@app.route('/')
def home(): return "رادار سلطان شغال ويصيد كل الفرص! 🦅"
def run():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']
active_trades = {}

def get_market_opportunities():
    print("🔄 الرادار يفحص كل الفرص المتاحة الآن...")
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
                    bot.send_message(CHAT_ID, f"🎯 **مبروك يا سلطان! تحقق الهدف**\n✅ سهم `{t}` وصل للمحطة الأولى: `${trade['t1']}` 💰")
                    del active_trades[t]
                    continue

            # --- التحليل الفني الشامل ---
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            df['sma20'] = ta.sma(df['close'], length=20)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
            rsi_now = df['rsi'].iloc[-1]
            ema_now = df['ema9'].iloc[-1]
            sma_now = df['sma20'].iloc[-1]

            # --- كاشف الفرص (حساس لجميع الحركات) ---
            status = None
            if rsi_now < 45: status = 'CALL' 
            elif rsi_now > 55: status = 'PUT'

            if status:
                # --- نظام حساب "درجة الثقة" (السر في النجاح) ---
                score = 30 # أساسي
                if vol_ratio > 1.5: score += 25 # قوة سيولة
                if (status == 'CALL' and p > ema_now) or (status == 'PUT' and p < ema_now): score += 20 # اتجاه صحيح
                if (status == 'CALL' and rsi_now < 30) or (status == 'PUT' and rsi_now > 70): score += 25 # منطقة ارتداد حقيقية
                
                # تصنيف القوة بالرموز
                if score >= 80: power = "🟢 ذهبية (ثقة ملكية 👑)"
                elif score >= 55: power = "🟡 متوسطة (مضاربة جيدة ✅)"
                else: power = "⚪ ضعيفة (مخاطرة عالية ⚠️)"

                # تحديد المحطات (الهدف والوقف بناءً على التذبذب)
                atr_val = df['atr'].iloc[-1]
                stop = round(p - (atr_val * 2), 2) if status == 'CALL' else round(p + (atr_val * 2), 2)
                target1 = round(p + (atr_val * 3), 2) if status == 'CALL' else round(p - (atr_val * 3), 2)

                active_trades[t] = {'type': status, 't1': target1}

                # --- رسالة المحلل الشاملة ---
                msg = (f"🚀 **فرصة مكتشفة: {t}**\n\n"
                       f"📊 **درجة الثقة: {score}%**\n"
                       f"💪 القوة: {power}\n"
                       f"------------------------------\n"
                       f"📈 النوع: {'🟢 CALL' if status == 'CALL' else '🔴 PUT'}\n"
                       f"💰 السعر: `${p}` | السيولة: {vol_ratio}x\n"
                       f"------------------------------\n"
                       f"📍 **خطة العمل:**\n"
                       f"🎯 الهدف: `{target1}`\n"
                       f"🛑 الوقف: `{stop}`\n\n"
                       f"📝 **ملاحظة:** تم إرسال الفرصة بناءً على طلبك لرؤية كل الفرص.")
                
                bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                time.sleep(2)

        except Exception as e: print(f"Error in {t}: {e}")

if __name__ == "__main__":
    Thread(target=run).start()
    print("✅ بوت سلطان (المحلل المحترف) يعمل الآن...")
    while True:
        get_market_opportunities()
        time.sleep(600)
