import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- رادار عبدالرحمن المتكامل بأهداف الشارت الثلاثة حية ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار الأهداف الثلاثة والسيولة شغال لايف 🦅🔥"

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

def get_live_data(ticker):
    try:
        # فريم 15 دقيقة لتصفية الضوضاء واقتناص الموجات الكبيرة
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=15m&range=5d"
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
    global last_signals
    
    for t in WATCHLIST:
        try:
            df = get_live_data(t)
            if df is None or len(df) < 30: continue

            p = round(df['close'].iloc[-1], 2)

            # حساب السوبر تريند والـ RSI لتأكيد الاتجاه
            sti = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
            df['rsi'] = ta.rsi(df['close'], length=14)
            if sti is None or df['rsi'].empty: continue
            
            trend_line = sti['SUPERTd_10_3.0'].iloc[-1]
            rsi_v = df['rsi'].iloc[-1]

            # فلتر كاش الحيتان والسيولة
            avg_vol = df['volume'].iloc[-11:-1].mean()
            last_complete_vol = df['volume'].iloc[-2]
            vol_ratio = round(last_complete_vol / avg_vol, 1) if avg_vol > 0 else 1.0

            # قراءة مستويات الشارت الحقيقية (الدعم والمقاومة الكلية لليوم)
            chart_high = round(df['high'].iloc[:-1].max(), 2)
            chart_low = round(df['low'].iloc[:-1].min(), 2)

            send_signal = False
            signal_type = ""

            # شروط الدخول: موجة واضحة + سيولة حيتان أعلى من المعدل الطبيعي
            if trend_line == 1 and rsi_v > 50 and vol_ratio >= 1.1:
                signal_type = "CALL 🟢"
                send_signal = True
            elif trend_line == -1 and rsi_v < 50 and vol_ratio >= 1.1:
                signal_type = "PUT 🔴"
                send_signal = True

            if send_signal:
                if last_signals.get(t) != signal_type:
                    
                    # 🛠️ الحسبة الهندسية للأهداف الثلاثة والوقف من الشارت بدون نسب مئوية ثابتة
                    if signal_type == "CALL 🟢":
                        max_target = chart_high if chart_high > p else round(p * 1.03, 2)
                        diff = (max_target - p) / 3
                        
                        target1 = round(p + diff, 2)
                        target2 = round(p + (diff * 2), 2)
                        target3 = round(max_target, 2)
                        
                        stop_loss_hard = chart_low
                        stop_loss_fast = round(p - (p - chart_low) * 0.5, 2) if chart_low < p else round(p * 0.99, 2)
                    else:
                        min_target = chart_low if chart_low < p else round(p * 0.97, 2)
                        diff = (p - min_target) / 3
                        
                        target1 = round(p - diff, 2)
                        target2 = round(p - (diff * 2), 2)
                        target3 = round(min_target, 2)
                        
                        stop_loss_hard = chart_high
                        stop_loss_fast = round(p + (chart_high - p) * 0.5, 2) if chart_high > p else round(p * 1.01, 2)

                    # رسالة منسقة بالملي تعزل التشتيت وتعطيك مستوياتك الصريحة
                    msg = (
                        f"🐋 **رادار عبدالرحمن الشامل - أهداف الموجة الحية**\n\n"
                        f"📌 **السهم المستهدف:** {t}\n"
                        f"📈 **إشارة الأوبشن:** {signal_type}\n"
                        f"💰 **سعر الدخول الحالي:** ${p}\n"
                        f"📊 **معدل سيولة الحيتان:** {vol_ratio}x\n"
                        f"----------------------------------\n"
                        f"🎯 **الهدف الأول:** ${target1}\n"
                        f"🎯 **الهدف الثاني:** ${target2}\n"
                        f"🎯 **الهدف الثالث (المقاومة/الدعم):** ${target3}\n"
                        f"----------------------------------\n"
                        f"🛑 **وقف خسارة مضاربي (قريب):** ${stop_loss_fast}\n"
                        f"🛑 **وقف الخسارة الرئيسي (الشارت):** ${stop_loss_hard}\n"
                        f"----------------------------------"
                    )
                    bot.send_message(CHAT_ID, msg)
                    last_signals[t] = signal_type
                    time.sleep(2)
        except:
            continue

def main():
    try:
        bot.send_message(CHAT_ID, "🦅 تم تحديث رادار الأهداف الثلاثة والوقف المزدوج بنجاح!\n- الأهداف مقسمة ومحسوبة بالملي من مستويات الشارت الفعلي لتأمين الأرباح أولاً بأول.")
    except Exception as e:
        print(e)

    while True:
        scan_market()
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    main()
