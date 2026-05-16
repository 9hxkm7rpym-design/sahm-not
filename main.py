import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات رادار عبدالرحمن ---
TOKEN = "8308789681:AAE10GeevJ5l5iBSPHKsT2HLzud4B2KP9hU"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن يعمل بكامل طاقته 🦅"

def run_flask():
    # هذا السطر مهم جداً لمنصة Render
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# القائمة الذهبية (22 سهم حلال ونشيط)
WATCHLIST = [
    'AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 
    'OXY', 'MSFT', 'GOOGL', 'META', 'AVGO', 'ASML', 'ADBE', 'CRM', 'PANW', 
    'SHOP', 'COST', 'SNAP', 'CVX'
]

# ذاكرة لمنع تكرار نفس الاتجاه (ما يرسل كول مرتين ورا بعض لنفس السهم)
last_signals = {}

def get_market_data():
    # رسالة ترحيب عند التشغيل للتأكد أن البوت اتصل بتليجرام
    try:
        bot.send_message(CHAT_ID, "🚀 تم تشغيل رادار عبدالرحمن بنجاح! الرادار يراقب السوق الآن 24/7.")
    except:
        print("خطأ في الاتصال بتليجرام، تأكد من الـ Token")

    while True:
        for t in WATCHLIST:
            try:
                # 1. سحب بيانات السوق (فريم 15 دقيقة)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                data = r['chart']['result'][0]
                df = pd.DataFrame(data['indicators']['quote'][0]).ffill()
                
                # جلب آخر عنوان خبر للسهم
                news_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={t}"
                news_r = requests.get(news_url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                latest_news = news_r['news'][0]['title'] if (news_r.get('news') and len(news_r['news']) > 0) else "لا توجد أخبار حديثة"

                # 2. الحسابات الفنية الدقيقة (الأرقام اللي تبيها)
                p = round(df['close'].iloc[-1], 2)
                res = round(df['high'].tail(20).max(), 2) # أعلى سعر (مقاومة)
                sup = round(df['low'].tail(20).min(), 2)  # أدنى سعر (دعم)
                
                # حساب RSI وتفسيره ببساطة
                df['rsi'] = ta.rsi(df['close'], length=14)
                rsi_v = round(df['rsi'].iloc[-1], 1)
                if rsi_v < 35: rsi_desc = "نازل بزيادة (فرصة ارتداد) 📉"
                elif rsi_v > 65: rsi_desc = "طالع بزيادة (انتبه من النزول) 📈"
                else: rsi_desc = "الزخم هادئ 💤"

                # حساب السيولة SMC (نسبة الفوليوم الحالي للمتوسط)
                vol_now = df['volume'].iloc[-1]
                vol_avg = df['volume'].tail(20).mean()
                vol_ratio = round(vol_now / vol_avg, 1)
                smc_desc = f"دخول هامور قوي ({vol_ratio}x) 🔥" if vol_ratio > 1.5 else "سيولة طبيعية ⚠️"

                # 3. منطق المدارس (يرسل لو مدرسة واحدة بس أعطت إشارة)
                status, score, schools = None, 0, []

                # المدرسة الكلاسيكية
                if p <= sup * 1.005: 
                    status, score = "CALL 🟢", score + 35
                    schools.append(f"✨ كلاسيكي: عند الدعم (${sup}) - منطقة شراء")
                elif p >= res * 0.995:
                    status, score = "PUT 🔴", score + 35
                    schools.append(f"🛑 كلاسيكي: عند المقاومة (${res}) - منطقة بيع")

                # مدرسة الزخم (RSI)
                if rsi_v < 40 or rsi_v > 60:
                    score += 30
                    schools.append(f"📊 RSI: {rsi_v} ({rsi_desc})")
                
                # مدرسة السيولة (SMC)
                if vol_ratio > 1.2:
                    score += 35
                    schools.append(f"💰 SMC: {smc_desc}")

                # 4. فلتر منع التكرار وإرسال التنبيه
                if status and (last_signals.get(t) != status):
                    msg = (
                        f"🦅 **رادار عبدالرحمن: {t}**\n"
                        f"----------------------------------\n"
                        f"📈 **الإشارة:** {status}\n"
                        f"💰 **السعر الحالي:** ${p}\n\n"
                        f"🛠 **تحليل المدارس:**\n" + "\n".join(schools) + "\n\n"
                        f"🎯 **الهدف الفني:** ${res if status == 'CALL 🟢' else sup}\n"
                        f"🛑 **الوقف الفني:** ${sup if status == 'CALL 🟢' else res}\n\n"
                        f"🔥 **درجة الثقة:** {score}%\n"
                        f"📰 **آخر خبر:** {latest_news}\n"
                        f"----------------------------------"
                    )
                    bot.send_message(CHAT_ID, msg)
                    last_signals[t] = status # حفظ الاتجاه عشان ما يزعجك بتكرار نفس النوع
                    time.sleep(2)

            except Exception as e:
                print(f"حدث خطأ في {t}: {e}")
        
        # فحص السوق كل 5 دقائق
        time.sleep(300)

if __name__ == "__main__":
    # تشغيل السيرفر والبوت معاً
    Thread(target=run_flask).start()
    get_market_data()
