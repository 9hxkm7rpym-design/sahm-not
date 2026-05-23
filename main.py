import telebot
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# --- إعدادات عبادي للتجربة ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

# قائمة مصغرة للتجربة الفورية
TEST_WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'AMZN', 'OXY']

def get_next_friday():
    today = datetime.now()
    days_ahead = 4 - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_friday = today + timedelta(days_ahead)
    return next_friday.strftime('%d%b%y').upper()

def get_live_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=15m&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10).json()
        result = r['chart']['result'][0]
        df = pd.DataFrame(result['indicators']['quote'][0])
        df['close'] = df['close'].ffill().bfill()
        df['high'] = df['high'].ffill().bfill()
        df['low'] = df['low'].ffill().bfill()
        df['volume'] = df['volume'].ffill().bfill()
        return df
    except: return None

def run_test_simulation():
    bot.send_message(CHAT_ID, "⚙️ **يا عبادي، تم تشغيل الفحص التجريبي بأسعار إغلاق السوق الحالية... جاري التحليل والإرسال!**", parse_mode='Markdown')
    
    trade_counter = 0
    expiry_date = get_next_friday()

    for t in TEST_WATCHLIST:
        df = get_live_data(t)
        if df is None or len(df) < 30: continue

        # 1. السعر الحالي (إغلاق الجمعة)
        p = round(df['close'].iloc[-1], 2)

        # 2. استخراج الدعوم والمقاومات الحقيقية (القمم والقيعان)
        df['pivot_high'] = df['high'][(df['high'] == df['high'].rolling(11, center=True).max())]
        df['pivot_low'] = df['low'][(df['low'] == df['low'].rolling(11, center=True).min())]
        all_highs = sorted(df['pivot_high'].dropna().unique())
        all_lows = sorted(df['pivot_low'].dropna().unique())

        # 3. حساب المؤشرات الفنية
        sti = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
        df['rsi'] = ta.rsi(df['close'], length=14)
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        
        if sti is None or df['rsi'].empty or adx_df is None or adx_df.empty: continue
        
        trend_line = sti['SUPERTd_10_3.0'].iloc[-1]
        rsi_v = df['rsi'].iloc[-1]
        adx_value = adx_df['ADX_14'].iloc[-1]

        avg_vol = df['volume'].iloc[-11:-1].mean()
        vol_ratio = round(df['volume'].iloc[-2] / avg_vol, 1) if avg_vol > 0 else 1.0

        # --- منظومة التنقيط الذكية (من 4 نقاط) ---
        score = 0
        
        # الاتجاه الصريح الافتراضي للتجربة بناء على آخر حركة
        signal_type = "CALL 🟢" if trend_line == 1 else "PUT 🔴"
        
        # فحص الشروط لجمع النقاط
        if trend_line == 1 or trend_line == -1: score += 1 # شرط الاتجاه
        if (signal_type == "CALL 🟢" and rsi_v > 50) or (signal_type == "PUT 🔴" and rsi_v < 50): score += 1 # شرط القوة والـ RSI
        if adx_value >= 20: score += 1 # شرط الخروج من النطاق العرضي
        if vol_ratio >= 1.2: score += 1 # شرط سيولة الحيتان العالية

        # تحديد التقييم النهائي بناءً على مجموع النقاط
        if score == 4: confidence = "قوية جداً (النخبة 🟩)"
        elif score == 3: confidence = "متوسطة الارتداد 🟨"
        else: confidence = "ضعيفة / تذبذب عرضي 🟥"

        # 4. الأهداف والوقف بناءً على الدعوم والمقاومات الحقيقية للشارت
        if signal_type == "CALL 🟢":
            highs_above = [round(h, 2) for h in all_highs if h > p]
            t1 = highs_above[0] if len(highs_above) > 0 else round(p * 1.01, 2)
            t2 = highs_above[1] if len(highs_above) > 1 else round(p * 1.02, 2)
            t3 = highs_above[2] if len(highs_above) > 2 else round(p * 1.04, 2)
            lows_below = [round(l, 2) for l in all_lows if l < p]
            sl = lows_below[-1] if len(lows_below) > 0 else round(p * 0.99, 2)
            opt_label = "CALL"
        else:
            lows_below = [round(l, 2) for l in all_lows if l < p]
            t1 = lows_below[-1] if len(lows_below) > 0 else round(p * 0.99, 2)
            t2 = lows_below[-2] if len(lows_below) > 1 else round(p * 0.98, 2)
            t3 = lows_below[-3] if len(lows_below) > 2 else round(p * 0.96, 2)
            highs_above = [round(h, 2) for h in all_highs if h > p]
            sl = highs_above[0] if len(highs_above) > 0 else round(p * 1.01, 2)
            opt_label = "PUT"

        # حساب سترايك تقريبي للعقد
        strike_val = int(p + 2) if opt_label == "CALL" else int(p - 2)

        # 5. بناء رسالة عبادي المنسقة والمنظمة
        trade_counter += 1
        msg = (
            f"🚀 **[ صفقة تجريبية رقم #{trade_counter} ]**\n\n"
            f"📊 **درجة الثقة الإجمالية:** {confidence} | `[{score} من 4]`\n"
            f"🔍 **قوة التريند (ADX):** `{round(adx_value, 1)}`\n"
            f"🐋 **فوليوم كاش الحيتان:** `{vol_ratio}x`\n"
            f"───────────────────\n"
            f"📌 **الـسـهـم:** `{t}`\n"
            f"📈 **الإتـجـاه المكتشف:** *{signal_type}*\n"
            f"💰 **سعر إغلاق السوق الحقيقي:** `${p}`\n"
            f"───────────────────\n"
            f"🎫 **بـيـانـات الـعـقـد (جاهز لـ سهْم)**\n"
            f"`{t} {expiry_date} {strike_val} {opt_label}`\n"
            f"───────────────────\n"
            f"🎯 **الـمـسـتـهـدفـات (دعوم ومقاومات الشارت)**\n"
            f"• 🔹 الهدف الأول: `${t1}`\n"
            f"• 🔹 الهدف الثاني: `${t2}`\n"
            f"• 🔹 الهدف الثالث: `${t3}`\n"
            f"───────────────────\n"
            f"🛑 **صـمـام الأمـان**\n"
            f"• 🚨 وقف خسارة قريب: `${sl}`\n"
            f"───────────────────"
        )
        
        try:
            bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
        except Exception as e:
            print(f"Error sending {t}: {e}")
            
    bot.send_message(CHAT_ID, "✅ **يا عبادي تم إرسال كافة الأسعار المتاحة بنظام التنقيط الجديد! شيك على التليجرام الآن.**", parse_mode='Markdown')

if __name__ == "__main__":
    run_test_simulation()
