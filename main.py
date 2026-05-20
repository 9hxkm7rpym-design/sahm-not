import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات رادار عبدالرحمن المتكامل ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن الخارق يعمل بكامل طاقته 🦅🔥"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# القائمة الذهبية المحدثة (الـ 22 القديمة + 10 شركات قوية ورخيصة)
WATCHLIST = [
    'AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 
    'OXY', 'MSFT', 'GOOGL', 'META', 'AVGO', 'ASML', 'ADBE', 'CRM', 'PANW', 
    'SHOP', 'COST', 'SNAP', 'CVX',
    'PLTR', 'XPEV', 'SOFI', 'F', 'PFE', 'AAL', 'PBR', 'KVUE', 'INTC', 'HOOD'
]

last_signals = {}

def get_market_data():
    try:
        bot.send_message(CHAT_ID, "🚀 تم تحديث القائمة! الرادار الآن يراقب 32 شركة تشمل الأسهم القوية والرخيصة مع التحليل المتكامل (درجة الثقة).")
    except Exception as e:
        print(f"خطأ في إرسال رسالة التحديث: {e}")

    while True:
        for t in WATCHLIST:
            try:
                # 1. سحب بيانات السوق (فريم 15 دقيقة)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                data = r['chart']['result'][0]
                df = pd.DataFrame(data['indicators']['quote'][0])
                df['close'] = df['close'].ffill()
                df['high'] = df['high'].ffill()
                df['low'] = df['low'].ffill()
                df['volume'] = df['volume'].ffill()
                
                # جلب آخر خبر
                news_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={t}"
                news_r = requests.get(news_url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                latest_news = news_r['news'][0]['title'] if (news_r.get('news') and len(news_r['news']) > 0) else "لا توجد أخبار حديثة"

                # 2. الحسابات الفنية
                p = round(df['close'].iloc[-1], 2)
                res = round(df['high'].tail(20).max(), 2) 
                sup = round(df['low'].tail(20).min(), 2)  
                
                # حساب المؤشرات باستخدام pandas_ta
                df['rsi'] = ta.rsi(df['close'], length=14)
                rsi_v = round(df['rsi'].iloc[-1], 1)
                
                # الماكد MACD (12, 26, 9)
                macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
                macd_line = macd_df['MACD_12_26_9'].iloc[-1]
                macd_signal = macd_df['MACDs_12_26_9'].iloc[-1]
                
                # قنوات بولينجر (20, 2) والموفينج EMA 20
                bb_df = ta.bbands(df['close'], length=20, std=2)
                bb_upper = bb_df['BBU_20_2.0'].iloc[-1]
                bb_lower = bb_df['BBL_20_2.0'].iloc[-1]
                df['ema20'] = ta.ema(df['close'], length=20)
                ema20_v = df['ema20'].iloc[-1]

                # سيولة الهوامير SMC
                vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)

                # 3. نظام النقاط وحساب الثقة الشامل (Score)
                score = 0
                schools = []
                signal_type = None

                # الفحص الأول: الاتجاه والموفينج (EMA 20)
                if p > ema20_v:
                    if p >= res * 0.995:
                        schools.append(f"✅ كلاسيكي: عند المقاومة (${res}) [حذر]")
                    elif p <= sup * 1.005:
                        score += 20
                        schools.append(f"✅ كلاسيكي: ارتداد من الدعم (${sup})")
                else:
                    if p >= res * 0.995:
                        score += 20
                        schools.append(f"✅ كلاسيكي: اصطدام بالمقاومة (${res})")
                    elif p <= sup * 1.005:
                        schools.append(f"✅ كلاسيكي: عند الدعم (${sup}) [حذر]")

                # الفحص الثاني: تقاطع الماكد MACD
                if macd_line > macd_signal:
                    macd_desc = "إيجابي 📈"
                    if macd_line > 0: score += 20
                else:
                    macd_desc = "سلبي 📉"
                    if macd_line < 0: score += 20
                schools.append(f"📊 تقاطع MACD: {macd_desc}")

                # الفحص الثالث: قنوات بولينجر للانفجار السعري
                if p >= bb_upper * 0.995:
                    bb_desc = "اختراق الخط العلوي (انفجار لأعلى) 💣"
                    score += 20
                    signal_type = "CALL 🟢"
                elif p <= bb_lower * 1.005:
                    bb_desc = "كسر الخط السفلي (انفجار لأسفل) 💣"
                    score += 20
                    signal_type = "PUT 🔴"
                else:
                    bb_desc = "داخل القنوات 💤"
                schools.append(f"🌐 بولينجر: {bb_desc}")

                # الفحص الرابع: مؤشر الـ RSI
                if rsi_v < 40:
                    rsi_desc = "منخفض (فرصة ارتداد) ⬇️"
                    if signal_type == "CALL 🟢": score += 20
                elif rsi_v > 60:
                    rsi_desc = "تضخم (قرب تصحيح) ⬆️"
                    if signal_type == "PUT 🔴": score += 20
                else:
                    rsi_desc = "متوسط 💤"
                schools.append(f"📈 مؤشر RSI: {rsi_v} ({rsi_desc})")

                # الفحص الخامس: السيولة وحجم التداول SMC
                if vol_ratio > 1.4:
                    score += 20
                    smc_desc = f"دخول سيولة ذكية قوية ({vol_ratio}x) 🔥"
                else:
                    smc_desc = f"سيولة طبيعية ({vol_ratio}x) ⚠️"
                schools.append(f"💰 السيولة SMC: {smc_desc}")

                # 4. إرسال التنبيه إذا كانت الثقة قوية وعندنا اتجاه واضح
                if signal_type and score >= 40:
                    if last_signals.get(t) != signal_type:
                        msg = (
                            f"🦅 **رادار عبدالرحمن الخارق: {t}**\n"
                            f"----------------------------------\n"
                            f"📈 **الإشارة:** {signal_type}\n"
                            f"💰 **السعر الحالي:** ${p}\n\n"
                            f"🛠 **التحليل الفني المتكامل:**\n" + "\n".join(schools) + "\n\n"
                            f"🎯 **الهدف المتوقع:** ${res if signal_type == 'CALL 🟢' else sup}\n"
                            f"🛑 **وقف الخسارة:** ${sup if signal_type == 'CALL 🟢' else res}\n\n"
                            f"🔥 **درجة الثقة الإجمالية:** {score}%\n"
                            f"📰 **آخر خبر:** {latest_news}\n"
                            f"----------------------------------"
                        )
                        bot.send_message(CHAT_ID, msg)
                        last_signals[t] = signal_type
                        time.sleep(2)

            except Exception as e:
                print(f"خطأ في تحليل سهم {t}: {e}")
        
        time.sleep(300) # فحص كل 5 دقائق

if __name__ == "__main__":
    Thread(target=run_flask).start()
    get_market_data()
