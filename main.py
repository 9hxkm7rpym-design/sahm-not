import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات رادار عبدالرحمن (التوكن الجديد) ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن يعمل بكامل طاقته 🦅"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# القائمة الذهبية (22 سهم حلال ونشيط)
WATCHLIST = [
    'AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 
    'OXY', 'MSFT', 'GOOGL', 'META', 'AVGO', 'ASML', 'ADBE', 'CRM', 'PANW', 
    'SHOP', 'COST', 'SNAP', 'CVX'
]

# ذاكرة لمنع تكرار نفس الاتجاه
last_signals = {}

def get_market_data():
    # رسالة ترحيب فورية عند التشغيل
    try:
        bot.send_message(CHAT_ID, "🚀 تم تشغيل رادار عبدالرحمن بنجاح! الرادار يراقب السوق الآن 24/7 بالتوكن الجديد.")
    except Exception as e:
        print(f"خطأ في إرسال رسالة الترحيب: {e}")

    while True:
        for t in WATCHLIST:
            try:
                # 1. سحب بيانات السوق
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                data = r['chart']['result'][0]
                df = pd.DataFrame(data['indicators']['quote'][0]).ffill()
                
                # جلب آخر عنوان خبر
                news_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={t}"
                news_r = requests.get(news_url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                latest_news = news_r['news'][0]['title'] if (news_r.get('news') and len(news_r['news']) > 0) else "لا توجد أخبار حديثة"

                # 2. الحسابات الفنية
                p = round(df['close'].iloc[-1], 2)
                res = round(df['high'].tail(20).max(), 2) 
                sup = round(df['low'].tail(20).min(), 2)  
                
                # RSI
                df['rsi'] = ta.rsi(df['close'], length=14)
                rsi_v = round(df['rsi'].iloc[-1], 1)
                rsi_desc = "فرصة ارتداد 📉" if rsi_v < 35 else "تشبع شراء 📈" if rsi_v > 65 else "هادئ 💤"

                # SMC (السيولة)
                vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
                smc_desc = f"سيولة قوية ({vol_ratio}x) 🔥" if vol_ratio > 1.5 else "سيولة طبيعية ⚠️"

                # 3. منطق الإشارات
                status, score, schools = None, 0, []

                if p <= sup * 1.005: 
                    status, score = "CALL 🟢", score + 35
                    schools.append(f"✅ كلاسيكي: عند الدعم (${sup})")
                elif p >= res * 0.995:
                    status, score = "PUT 🔴", score + 35
                    schools.append(f"✅ كلاسيكي: عند المقاومة (${res})")

                if rsi_v < 40 or rsi_v > 60:
                    score += 30
                    schools.append(f"📊 RSI: {rsi_v} ({rsi_desc})")
                
                if vol_ratio > 1.2:
                    score += 35
                    schools.append(f"💰 SMC: {smc_desc}")

                # 4. إرسال التنبيه
                if status and (last_signals.get(t) != status):
                    msg = (
                        f"🦅 **رادار عبدالرحمن: {t}**\n"
                        f"----------------------------------\n"
                        f"📈 **الإشارة:** {status}\n"
                        f"💰 **السعر:** ${p}\n\n"
                        f"🛠 **التحليل:**\n" + "\n".join(schools) + "\n\n"
                        f"🎯 **الهدف:** ${res if status == 'CALL 🟢' else sup}\n"
                        f"🛑 **الوقف:** ${sup if status == 'CALL 🟢' else res}\n\n"
                        f"🔥 **الثقة:** {score}%\n"
                        f"📰 **الخبر:** {latest_news}\n"
                        f"----------------------------------"
                    )
                    bot.send_message(CHAT_ID, msg)
                    last_signals[t] = status 
                    time.sleep(2)

            except Exception as e:
                print(f"خطأ في {t}: {e}")
        
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    get_market_data()
