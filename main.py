import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات رادار عبدالرحمن الملكي ذو الفريمين ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن المطور (5 دقائق + ساعة) يعمل بأعلى كفاءة 🦅🔥"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# القائمة الذهبية المحدثة (32 شركة من النخبة)
WATCHLIST = [
    'AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 
    'OXY', 'MSFT', 'GOOGL', 'META', 'AVGO', 'ASML', 'ADBE', 'CRM', 'PANW', 
    'SHOP', 'COST', 'SNAP', 'CVX',
    'PLTR', 'XPEV', 'SOFI', 'F', 'PFE', 'AAL', 'PBR', 'KVUE', 'INTC', 'HOOD'
]

# ذاكرة البوت لمنع تكرار الإشارات المزعجة
last_signals = {}

def analyze_ticker(t, interval, range_data, mode_name):
    global last_signals
    try:
        # 1. سحب بيانات السوق الحية
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval={interval}&range={range_data}"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        
        if 'chart' not in r or r['chart']['result'] is None:
            return
            
        data = r['chart']['result'][0]
        df = pd.DataFrame(data['indicators']['quote'][0])
        df['open'] = df['open'].ffill().bfill()
        df['close'] = df['close'].ffill().bfill()
        df['high'] = df['high'].ffill().bfill()
        df['low'] = df['low'].ffill().bfill()
        df['volume'] = df['volume'].ffill().bfill()

        # التحقق من توفر كمية بيانات كافية للحسابات
        if len(df) < 20:
            return

        # حسابات السعر والدعم والمقاومة الكلاسيكية
        p = round(df['close'].iloc[-1], 2)
        res = round(df['high'].tail(20).max(), 2)
        sup = round(df['low'].tail(20).min(), 2)

        # حساب مؤشرات الزخم (MACD + RSI)
        df['rsi'] = ta.rsi(df['close'], length=14)
        if df['rsi'].empty or pd.isna(df['rsi'].iloc[-1]): return
        rsi_v = round(df['rsi'].iloc[-1], 1)
        
        macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd_df is None or macd_df.empty: return
        macd_line = macd_df['MACD_12_26_9'].iloc[-1]
        macd_signal = macd_df['MACDs_12_26_9'].iloc[-1]

        # حساب المتوسط EMA 20 وقنوات بولينجر للانفجار
        df['ema20'] = ta.ema(df['close'], length=20)
        ema20_v = df['ema20'].iloc[-1]
        
        bb_df = ta.bbands(df['close'], length=20, std=2)
        if bb_df is None or bb_df.empty: return
        bb_upper = bb_df['BBU_20_2.0'].iloc[-1]
        bb_lower = bb_df['BBL_20_2.0'].iloc[-1]

        # فحص السيولة الفورية وحركة الحيتان (SMC)
        mean_vol = df['volume'].tail(20).mean()
        vol_ratio = round(df['volume'].iloc[-1] / mean_vol, 1) if mean_vol > 0 else 1.0
        
        # رادار الحيتان الخاص: رصد الشموع الاندفاعية الضخمة والفوليوم العالي
        std_close = df['close'].tail(20).std()
        is_whale_present = vol_ratio > 1.5 or (abs(df['close'].iloc[-1] - df['open'].iloc[-1]) > std_close * 2 if std_close > 0 else False)

        score = 0
        schools = []
        signal_type = None

        # [1] فحص الزخم والتقاطعات (MACD) - 20%
        if macd_line > macd_signal:
            signal_type = "CALL 🟢"
            score += 20
            schools.append("📊 الزخم (MACD): إيجابي وتصاعدي 📈")
        else:
            signal_type = "PUT 🔴"
            score += 20
            schools.append("📊 الزخم (MACD): سلبي وتنازلي 📉")

        # [2] فحص الاتجاه العام (EMA 20) - 20%
        if (signal_type == "CALL 🟢" and p > ema20_v) or (signal_type == "PUT 🔴" and p < ema20_v):
            score += 20
            schools.append("📈 الاتجاه: متناسق ومؤيد للحركة فوق/تحت متوسط EMA 20")

        # [3] فحص مناطق الحيتان الكلاسيكية (الدعم والمقاومة) - 20%
        if signal_type == "CALL 🟢" and p <= sup * 1.01:
            score += 20
            schools.append(f"✅ كلاسيكي: ارتداد من منطقة طلب ودعم حيتان قوية (${sup})")
        elif signal_type == "PUT 🔴" and p >= res * 0.99:
            score += 20
            schools.append(f"✅ كلاسيكي: اصطدام بمنطقة عرض ومقاومة حيتان قوية (${res})")

        # [4] فحص الانفجار السعري وضغط النطاق (Bollinger Bands) - 20%
        if (signal_type == "CALL 🟢" and p >= bb_upper * 0.99) or (signal_type == "PUT 🔴" and p <= bb_lower * 1.01):
            score += 20
            schools.append("🌐 بولينجر: ضغط وانفجار سعري خارج القنوات 💣")

        # [5] فحص سيولة صناع السوق (SMC) - 20%
        if is_whale_present:
            score += 20
            schools.append(f"💰 رادار الحيتان: رصد دخول سيولة ضخمة وأوامر مؤسساتية ({vol_ratio}x) 🔥")
        else:
            schools.append(f"💰 السيولة: حجم تداول طبيعي ومستقر ({vol_ratio}x)")

        # فلتر أمان الـ RSI لمنع مصايد القمم والقيعان تضخم السعر
        if rsi_v > 65 and signal_type == "CALL 🟢": score -= 10
        if rsi_v < 35 and signal_type == "PUT 🔴": score -= 10

        # مرشح الإرسال الصارم: لا يمر إلا الصفقات الموثوقة بنسبة 60% فما فوق
        if signal_type and score >= 60:
            signal_key = f"{t}_{mode_name}"
            if last_signals.get(signal_key) != signal_type:
                # سحب آخر خبر يؤثر على السهم
                news_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={t}"
                news_r = requests.get(news_url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                latest_news = news_r['news'][0]['title'] if (news_r.get('news') and len(news_r['news']) > 0) else "لا توجد أخبار مؤثرة حالياً"

                msg = (
                    f"🦅 **رادار عبدالرحمن الخارق [{mode_name}]**\n"
                    f"📌 **السهم:** {t}\n"
                    f"----------------------------------\n"
                    f"📈 **نوع الصفقة المستهدفة:** {signal_type}\n"
                    f"💰 **سعر الدخول الحالي:** ${p}\n\n"
                    f"🛠 **تحليل عقل الحيتان والزخم:**\n" + "\n".join(schools) + "\n\n"
                    f"🎯 **الهدف الفني الأول:** ${res if signal_type == 'CALL 🟢' else sup}\n"
                    f"🛑 **وقف الخسارة الصارم:** ${sup if signal_type == 'CALL 🟢' else res}\n\n"
                    f"🔥 **درجة الثقة والموثوقية:** {score}%\n"
                    f"📰 **آخر خبر للسهم:** {latest_news}\n"
                    f"----------------------------------"
                )
                bot.send_message(CHAT_ID, msg)
                last_signals[signal_key] = signal_type
                time.sleep(2)

    except Exception as e:
        print(f"خطأ في تحليل {t} فريم {interval}: {e}")

def get_market_data():
    try:
        bot.send_message(CHAT_ID, "🚀 تم إطلاق رادار عبدالرحمن المزدوج بنجاح!\n- فريم 5 دقائق شغال يصيد صفقات يومية بكثرة وبسرعة ⚡️\n- فريم 1 ساعة شغال يصيد صفقات الحيتان (حق كم يوم) 💎\nكل الأخطاء السابقة تم تصفيرها بنجاح!")
    except Exception as e:
        print(f"خطأ في إرسال رسالة التشغيل: {e}")

    while True:
        for t in WATCHLIST:
            # مسار الصيد السريع والوفير (5 دقائق)
            analyze_ticker(t, '5m', '1d', 'صفقة يومية سريعة ⚡️')
            # مسار الصيد الموزون والمطول (1 ساعة)
            analyze_ticker(t, '1h', '5d', 'صفقة أبو كم يوم 💎')
        time.sleep(300) # فحص دوري مؤتمت كل 5 دقائق للشركات كاملة

if __name__ == "__main__":
    Thread(target=run_flask).start()
    get_market_data()
