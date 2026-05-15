import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- الإعدادات الصارمة (إرسال فقط) ---
TOKEN = "8308789681:AAE10GeevJ5l5iBSPHKsT2HLzud4B2KP9hU"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home(): return "رادار سلطان الصامت يعمل بنجاح 🦅"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# قائمة الأسهم المختارة بعناية
WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 'OXY', 'CVX', 'RBLX']

def get_market_opportunities():
    print("بدأ الرادار في مراقبة السوق بصمت...")
    while True:
        for t in WATCHLIST:
            try:
                # جلب البيانات من ياهو فاينانس
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                data = r['chart']['result'][0]['indicators']['quote'][0]
                df = pd.DataFrame(data).ffill()
                
                # حساب المؤشرات الفنية
                p = round(df['close'].iloc[-1], 2)
                res = round(df['high'].tail(30).max(), 2)
                sup = round(df['low'].tail(30).min(), 2)
                df['macd_h'] = ta.macd(df['close'])['MACDh_12_26_9']
                vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
                
                status, scenario, score = None, "", 50
                
                # فلتر القناص الصارم (ثقة 80%+)
                if p >= res * 0.998 and df['macd_h'].iloc[-1] < df['macd_h'].iloc[-2]:
                    status, scenario = "PUT 🔴", f"⚠️ فخ صعودي عند مقاومة {res}"
                    if vol_ratio > 1.5: score += 35
                elif p <= sup * 1.002 and df['macd_h'].iloc[-1] > df['macd_h'].iloc[-2]:
                    status, scenario = "CALL 🟢", f"✅ ارتداد من دعم {sup}"
                    if vol_ratio > 1.5: score += 35

                # الإرسال فقط في حال توفرت الشروط الصعبة
                if status and score >= 80:
                    msg = (f"🦅 **تنبيه القناص: {t}**\n"
                           f"------------------\n"
                           f"🎬 السيناريو: {scenario}\n"
                           f"🎯 الثقة: {score}%\n"
                           f"📈 الاتجاه: {status} | السعر: ${p}\n"
                           f"📋 Strike: {int(round(p))}\n"
                           f"------------------\n"
                           f"ملاحظة: البوت في وضع الصمت (إرسال فقط).")
                    bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                    print(f"تم إرسال تنبيه لسهم {t}")
                    time.sleep(5)
            except Exception as e:
                print(f"خطأ في فحص {t}: {e}")
                pass
        time.sleep(300) # فحص شامل كل 5 دقائق

if __name__ == "__main__":
    # تشغيل السيرفر والرادار فقط (بدون polling)
    Thread(target=run_flask).start()
    get_market_opportunities()
