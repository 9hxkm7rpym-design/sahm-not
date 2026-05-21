import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- منظومة عبدالرحمن الفورية بنظام الدرجات ومناطق الدخول الدقيقة ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن الشامل شغال لايف 🦅🔥"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# القائمة النخبة الـ 32 شركة
WATCHLIST = [
    'AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 
    'OXY', 'MSFT', 'GOOGL', 'META', 'AVGO', 'ASML', 'ADBE', 'CRM', 'PANW', 
    'SHOP', 'COST', 'SNAP', 'CVX',
    'PLTR', 'XPEV', 'SOFI', 'F', 'PFE', 'AAL', 'PBR', 'KVUE', 'INTC', 'HOOD'
]

last_signals = {}
last_signal_times = {}

def get_live_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=10).json()
        
        if 'chart' not in r or r['chart']['result'] is None: return None
        
        result = r['chart']['result'][0]
        df = pd.DataFrame(result['indicators']['quote'][0])
        df['close'] = df['close'].ffill().bfill()
        df['high'] = df['high'].ffill().bfill()
        df['low'] = df['low'].ffill().bfill()
        df['volume'] = df['volume'].ffill().bfill()
        return df
    except:
        return None

def scan_market():
    global last_signals, last_signal_times
    current_time_now = time.time()
    
    for t in WATCHLIST:
        try:
            df = get_live_data(t)
            if df is None or len(df) < 25: continue

            p = round(df['close'].iloc[-1], 2)

            # حساب المؤشرات الفنية
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema9'] = ta.ema(df['close'], length=9)
            
            if df['rsi'].empty or df['ema9'].empty: continue
            
            rsi_v = round(df['rsi'].iloc[-1], 1)
            ema9_v = df['ema9'].iloc[-1]

            # حساب السيولة اللحظية
            avg_vol = df['volume'].iloc[-11:-1].mean()
            last_complete_vol = df['volume'].iloc[-2]
            vol_ratio = round(last_complete_vol / avg_vol, 1) if avg_vol > 0 else 1.0

            # قراءة مستويات القمم والقيعان للشارت اليومي
            chart_high = round(df['high'].iloc[:-1].max(), 2)
            chart_low = round(df['low'].iloc[:-1].min(), 2)

            send_signal = False
            signal_type = ""

            if p >= (chart_high * 0.995):
                signal_type = "CALL 🟢"
                send_signal = True
            elif p <= (chart_low * 1.005):
                signal_type = "PUT 🔴"
                send_signal = True

            if send_signal:
                # فلتر حظر الإشارة العكسية لمدة 45 دقيقة لمنع التشتيت
                if t in last_signal_times:
                    if current_time_now - last_signal_times[t] < 2700: 
                        continue 

                if last_signals.get(t) != signal_type:
                    
                    # فرز الدرجات
                    if vol_ratio >= 1.5 and ((signal_type == "CALL 🟢" and rsi_v > 55 and p > ema9_v) or (signal_type == "PUT 🔴" and rsi_v < 45 and p < ema9_v)):
                        confidence = "عــالــيــة جــداً (النخبة) 🟩"
                        tag = "💎 [دخول كاش الحيتان SMC]"
                        analysis = f"تطابق كامل للمواصفات! السيولة ضخمة جداً ({vol_ratio}x) والاختراق مؤكد بزخم فني حاد."
                    elif vol_ratio >= 1.0:
                        confidence = "متوسطة (مضاربية سريعة) 🟨"
                        tag = "⚡️ [اختراق زخم لحظي]"
                        analysis = f"السهم يتحرك عند أطراف الشارت مع سيولة مقبولة ({vol_ratio}x). الحركة مناسبة للمضاربة السريعة."
                    else:
                        confidence = "ضعيفة (مخاطرة عالية) 🟥"
                        tag = "⚠️ [تنبيه سلوك سعري]"
                        analysis = f"السعر عند أطراف الشارت لكن السيولة ضعيفة ({vol_ratio}x). قد يكون الاختراق وهمياً، احذر من الدخول المتأخر!"

                    # 🎯 التعديل الذهبي: تحديد منطقة الدخول الآمنة والأهداف الفنية
                    if signal_type == "CALL 🟢":
                        entry_zone = f"${chart_high} إلى ${round(chart_high * 1.003, 2)}" # حول القمة المخترقة بالظبط
                        target = round(chart_high * 1.02, 2) # المقاومة التالية
                        stop_loss = chart_low # الدعم الرئيسي (القاع)
                    else:
                        entry_zone = f"${chart_low} إلى ${round(chart_low * 0.997, 2)}" # حول القاع المكسور بالظبط
                        target = round(chart_low * 0.98, 2) # الدعم التالي
                        stop_loss = chart_high # المقاومة الرئيسية (القمة)

                    msg = (
                        f"{tag} **رادار عبدالرحمن الشامل لمستويات الشارت**\n\n"
                        f"🎯 **درجة قوة الصفقة:** {confidence}\n"
                        f"📌 **السهم المستهدف:** {t}\n"
                        f"📈 **إشارة الأوبشن:** {signal_type}\n"
                        f"💰 **السعر الحالي لايف:** ${p}\n"
                        f"----------------------------------\n"
                        f"🚪 **منطقة الدخول الآمنة 🔑:** {entry_zone}\n"
                        f"⚠️ *(إذا السعر الحالي أبعد وأغلى من المنطقة، انتظر ريتست ولا تلحق السهم)*\n"
                        f"----------------------------------\n"
                        f"🔍 **التحليل الفني والسيولة:**\n{analysis}\n\n"
                        f"📊 **معدل تدفق الكاش:** {vol_ratio}x\n"
                        f"🧭 **مؤشر القوة RSI:** {rsi_v}\n"
                        f"🎯 **الهدف الفني (المقاومة/الدعم):** ${target}\n"
                        f"🛑 **وقف الخسارة الفني (الدعم/المقاومة):** ${stop_loss}\n"
                        f"----------------------------------"
                    )
                    bot.send_message(CHAT_ID, msg)
                    last_signals[t] = signal_type
                    last_signal_times[t] = current_time_now
                    time.sleep(2)
        except:
            continue

def main():
    try:
        bot.send_message(CHAT_ID, "🦅 تم تحديث الرادار النهائي بنجاح!\n- تم إضافة سطر 'منطقة الدخول الآمنة' لحمايتك من الدخول العشوائي بأسعار غالية.")
    except Exception as e:
        print(e)

    while True:
        scan_market()
        time.sleep(180)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    main()
