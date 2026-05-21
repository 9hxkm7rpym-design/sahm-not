import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os
from datetime import datetime, timedelta

# --- إعدادات منظومة عبدالرحمن الشاملة المحدثة زمنيًا (نسخة الأمان الصارمة) ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن المطور يعمل ويقنص السيولة لايف 🦅🔥"

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

def get_market_data(t, interval, range_data):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval={interval}&range={range_data}"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if 'chart' not in r or r['chart']['result'] is None: return None
        
        data = r['chart']['result'][0]
        df = pd.DataFrame(data['indicators']['quote'][0])
        df['open'] = df['open'].ffill().bfill()
        df['close'] = df['close'].ffill().bfill()
        df['high'] = df['high'].ffill().bfill()
        df['low'] = df['low'].ffill().bfill()
        df['volume'] = df['volume'].ffill().bfill()
        return df
    except:
        return None

def is_market_open():
    """حساب توقيت السعودية بدقة عبر زيادة 3 ساعات على التوقيت العالمي وبدون مكاتب خارجية"""
    now_utc = datetime.utcnow()
    now_sa = now_utc + timedelta(hours=3)
    
    # أيام عمل السوق الأمريكي من الاثنين إلى الجمعة
    if now_sa.weekday() >= 5: 
        return False
        
    current_time = now_sa.strftime("%H:%M")
    # فترة التداول بتوقيت السعودية: من 16:30 (4:30 عصراً) إلى 23:00 (11:00 بالليل)
    return "16:30" <= current_time <= "23:00"

def check_spy_trend():
    df_spy = get_market_data('SPY', '5m', '1d')
    if df_spy is None or len(df_spy) < 10: return "NEUTRAL"
    spy_macd = ta.macd(df_spy['close'], fast=12, slow=26, signal=9)
    if spy_macd is None: return "NEUTRAL"
    return "BULLISH" if spy_macd['MACD_12_26_9'].iloc[-1] > spy_macd['MACDs_12_26_9'].iloc[-1] else "BEARISH"

def analyze_ticker(t):
    global last_signals
    try:
        df = get_market_data(t, '5m', '1d')
        if df is None or len(df) < 20: return

        # 1. حساب المؤشرات الفنية
        macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['rsi'] = ta.rsi(df['close'], length=14)
        if macd_df is None or df['rsi'].empty: return
        
        macd_line = macd_df['MACD_12_26_9'].iloc[-1]
        macd_signal = macd_df['MACDs_12_26_9'].iloc[-1]
        rsi_v = round(df['rsi'].iloc[-1], 1)
        p = round(df['close'].iloc[-1], 2)

        # 2. حساب الدعم والمقاومة والسيولة (SMC)
        res = round(df['high'].tail(20).max(), 2)
        sup = round(df['low'].tail(20).min(), 2)
        mean_vol = df['volume'].tail(20).mean()
        vol_ratio = round(df['volume'].iloc[-1] / mean_vol, 1) if mean_vol > 0 else 1.0
        
        is_heavy_cash = vol_ratio >= 1.5

        # 3. فحص مستويات ما قبل الافتتاح
        df_pm = get_market_data(t, '30m', '1d')
        pm_high = df_pm['high'].iloc[:13].max() if df_pm is not None and len(df_pm) >= 13 else res
        pm_low = df_pm['low'].iloc[:13].min() if df_pm is not None and len(df_pm) >= 13 else sup

        # 4. اتجاه السوق العام
        spy_status = check_spy_trend()

        send_signal = False
        signal_type = None

        if macd_line > macd_signal:
            signal_type = "CALL 🟢"
            send_signal = True
        elif macd_line < macd_signal:
            signal_type = "PUT 🔴"
            send_signal = True

        if send_signal and signal_type:
            signal_key = f"{t}_live"
            if last_signals.get(signal_key) != signal_type:
                
                confidence_score = "متوسطة 🟨"
                color_tag = "⚡️"
                reason = "الصفقة مدعومة بزخم فني طبيعي وسيولة مضاربية متوفرة."

                if signal_type == "CALL 🟢":
                    if is_heavy_cash and spy_status == "BULLISH" and p >= pm_high:
                        confidence_score = "عــالــيــة جــداً 🟩"
                        color_tag = "💎 [دخول الحيتان الكبار]"
                        reason = "توافق صاعق! سيولة حيتان ضخمة (SMC)، السوق العام صاعد، وتم اختراق قمة الافتتاح بالملي."
                    elif not is_heavy_cash or p >= res * 0.99 or spy_status == "BEARISH":
                        confidence_score = "ضعيفة 🟥"
                        color_tag = "⚠️ [تنبيه مخاطرة]"
                        reason = "الصفقة قريبة من المقاومة (السقف) أو الفوليوم ضعيف، والسوق العام لا يدعم الصعود حالياً."
                
                elif signal_type == "PUT 🔴":
                    if is_heavy_cash and spy_status == "BEARISH" and p <= pm_low:
                        confidence_score = "عــالــيــة جــداً 🟩"
                        color_tag = "💎 [دخول الحيتان الكبار]"
                        reason = "كبس سيولة بيعية ضخمة (SMC)، والسوق العام منهار، وتم كسر قاع الافتتاح لأسفل."
                    elif not is_heavy_cash or p <= sup * 1.01 or spy_status == "BULLISH":
                        confidence_score = "ضعيفة 🟥"
                        color_tag = "⚠️ [تنبيه مخاطرة]"
                        reason = "السهم قريب من مناطق دعم تاريخية (الأرض) أو السيولة ضعيفة، والسوق العام صامد."

                news_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={t}"
                news_r = requests.get(news_url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                latest_news = news_r['news'][0]['title'] if (news_r.get('news') and len(news_r['news']) > 0) else "لا توجد أخبار مؤثرة حالياً"

                msg = (
                    f"{color_tag} **رادار عبدالرحمن الشامل للسيولة والمؤشرات**\n\n"
                    f"🎯 **نسبة النجاح المتوقعة:** {confidence_score}\n"
                    f"📌 **السهم المستهدف:** {t}\n"
                    f"📈 **إشارة الأوبشن:** {signal_type}\n"
                    f"💰 **سعر السهم الحالي:** ${p}\n"
                    f"----------------------------------\n"
                    f"🔍 **تحليل الميزان والسيولة:**\n{reason}\n\n"
                    f"📊 **حجم كاش الحيتان (SMC):** {vol_ratio}x من الطبيعي\n"
                    f"🎯 **الهدف القادم:** ${res if signal_type == 'CALL 🟢' else sup}\n"
                    f"🛑 **وقف الخسارة الصارم:** ${sup if signal_type == 'CALL 🟢' else res}\n"
                    f"📉 **مؤشر السوق العام SPY:** {spy_status}\n"
                    f"📰 **آخر خبر للسهم:** {latest_news}\n"
                    f"----------------------------------"
                )
                bot.send_message(CHAT_ID, msg)
                last_signals[signal_key] = signal_type
                time.sleep(2)

    except Exception as e:
        print(f"خطأ في تحليل {t}: {e}")

def main_loop():
    try:
        bot.send_message(CHAT_ID, "🚀 تم إطلاق التحديث الآمن بنجاح وبدون مكاتب خارجية!\nالرادار شغال الحين وبدأ يفحص الأسهم لايف فوراً وبأعلى دقة زمنية. راقب القناة الحين! 🔥")
    except Exception as e:
        print(e)

    while True:
        if is_market_open():
            for t in WATCHLIST:
                analyze_ticker(t)
        time.sleep(180) # فحص متواصل كل 3 دقائق لاقتناص حركة الكاش

if __name__ == "__main__":
    Thread(target=run_flask).start()
    main_loop()
