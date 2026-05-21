import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os
from datetime import datetime, timedelta

# --- منظومة عبدالرحمن الملكية الشاملة (نسخة السترايك الحقيقي المطابق للتطبيقات) ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن بالسترايكات الحقيقية شغال لايف 🦅🔥"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = [
    'AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 
    'OXY', 'MSFT', 'GOOGL', 'META', 'AVGO', 'ASML', 'ADBE', 'CRM', 'PANW', 
    'SHOP', 'COST', 'SNAP', 'CVX',
    'PLTR', 'XPEV', 'SOFI', 'F', 'PFE', 'AAL', 'PBR', 'KVUE', 'INTC', 'HOOD'
]

last_signals = {}
active_trades = {}

# 📅 دالة ذكية لحساب تاريخ أقرب جمعة (انتهاء العقد الأسبوعي)
def get_next_friday():
    today = datetime.now()
    days_ahead = 4 - today.weekday() # 4 تعني يوم الجمعة
    if days_ahead <= 0: days_ahead += 7 # إذا كان اليوم جمعة أو ويكند يجيب الجمعة القادمة
    next_friday = today + timedelta(days_ahead)
    return next_friday.strftime('%d%b%y').upper()

# 🎯 دالة هندسة السترايك الحقيقي لمنع الاختلاف مع تطبيق سهْم
def calculate_real_strike(ticker, current_price, option_type):
    # تحديد الفواصل بناءً على سلوك السهم في السوق الأمريكي
    if ticker in ['NVDA', 'TSLA', 'MSFT', 'META', 'AVGO', 'ASML']:
        interval = 2.5 if current_price < 200 else 5.0
    elif ticker in ['AAPL', 'AMD', 'AMZN', 'CRM', 'ADBE', 'COST', 'PANW', 'OXY', 'CVX']:
        interval = 1.0 if current_price < 100 else 2.5
    else:
        interval = 0.5 if current_price < 20 else 1.0

    # تقريب السعر لأقرب سترايك حقيقي موجود في سلسلة العقود
    base = round(current_price / interval) * interval
    
    if option_type == "CALL":
        # في الكول نأخذ السترايك الأعلى القريب (خارج السيولة حبة OTM)
        strike = base + interval if base <= current_price else base
    else:
        # في البوت نأخذ السترايك الأقل القريب
        strike = base - interval if base >= current_price else base
        
    # إذا كان الرقم صحيح بدون فواصل نشيل الـ .0 لتطابق التطبيق
    return int(strike) if strike % 1 == 0 else round(strike, 2)

def get_live_data(ticker):
    try:
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
    except: return None

def scan_market():
    global last_signals, active_trades
    
    for t in WATCHLIST:
        try:
            df = get_live_data(t)
            if df is None or len(df) < 30: continue

            p = round(df['close'].iloc[-1], 2)

            # --- متابعة الأهداف اللحظية لايف ---
            if t in active_trades:
                trade = active_trades[t]
                if trade['type'] == "CALL 🟢":
                    if p >= trade['t1'] and not trade['t1_hit']:
                        bot.send_message(CHAT_ID, f"🎯 **تحقق الهدف الأول يا عبدالرحمن!** ✅\nسهم `{t}` وصل للمحطة الأولى: `${trade['t1']}` 💰")
                        trade['t1_hit'] = True
                    if p >= trade['t2'] and not trade['t2_hit']:
                        bot.send_message(CHAT_ID, f"🚀 **كفوو! تحقق الهدف الثاني** ✅\nسهم `{t}` طار للمحطة الثانية: `${trade['t2']}` 🔥")
                        trade['t2_hit'] = True
                    if p >= trade['t3']:
                        bot.send_message(CHAT_ID, f"👑 **يا ملك! قفلنا الهدف الثالث بالكامل** ✅\nسهم `{t}` حقق مستهدفه النهائي: `${trade['t3']}` 💎")
                        del active_trades[t]
                        continue
                    if p <= trade['sl']:
                        bot.send_message(CHAT_ID, f"🛑 **تنبيه الوقف القريب**\nسهم `{t}` ضرب الوقف عند: `${trade['sl']}` 🧨")
                        del active_trades[t]
                        continue
                elif trade['type'] == "PUT 🔴":
                    if p <= trade['t1'] and not trade['t1_hit']:
                        bot.send_message(CHAT_ID, f"🎯 **تحقق الهدف الأول يا عبدالرحمن!** ✅\nسهم `{t}` (PUT) وصل للمحطة الأولى: `${trade['t1']}` 💰")
                        trade['t1_hit'] = True
                    if p <= trade['t2'] and not trade['t2_hit']:
                        bot.send_message(CHAT_ID, f"🚀 **كفوو! تحقق الهدف الثاني** ✅\nسهم `{t}` (PUT) نزل للمحطة الثانية: `${trade['t2']}` 🔥")
                        trade['t2_hit'] = True
                    if p <= trade['t3']:
                        bot.send_message(CHAT_ID, f"👑 **يا ملك! قفلنا الهدف الثالث بالكامل** ✅\nسهم `{t}` (PUT) حقق مستهدفه النهائي: `${trade['t3']}` 💎")
                        del active_trades[t]
                        continue
                    if p >= trade['sl']:
                        bot.send_message(CHAT_ID, f"🛑 **تنبيه الوقف القريب**\nسهم `{t}` (PUT) ضرب الوقف عند: `${trade['sl']}` 🧨")
                        del active_trades[t]
                        continue

            # --- التحليل الفني ورصد الاتجاه ---
            sti = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
            df['rsi'] = ta.rsi(df['close'], length=14)
            if sti is None or df['rsi'].empty: continue
            
            trend_line = sti['SUPERTd_10_3.0'].iloc[-1]
            rsi_v = df['rsi'].iloc[-1]

            avg_vol = df['volume'].iloc[-11:-1].mean()
            last_complete_vol = df['volume'].iloc[-2]
            vol_ratio = round(last_complete_vol / avg_vol, 1) if avg_vol > 0 else 1.0

            chart_high = round(df['high'].iloc[:-1].max(), 2)
            chart_low = round(df['low'].iloc[:-1].min(), 2)

            send_signal = False
            signal_type = ""

            if trend_line == 1 and rsi_v > 50:
                signal_type = "CALL 🟢"
                send_signal = True
            elif trend_line == -1 and rsi_v < 50:
                signal_type = "PUT 🔴"
                send_signal = True

            if send_signal:
                if last_signals.get(t) != signal_type:
                    
                    if vol_ratio >= 1.3:
                        confidence = "النخبة (سيولة حيتان ضخمة) 🟩"
                        icon = "💎"
                    elif vol_ratio >= 0.8:
                        confidence = "متوسطة (موجة زخم طبيعية) 🟨"
                        icon = "⚡"
                    else:
                        confidence = "ضعيفة (مخاطرة عالية) 🟥"
                        icon = "⚠️"

                    # حسبة مستويات الشارت
                    if signal_type == "CALL 🟢":
                        max_target = chart_high if chart_high > p else round(p * 1.03, 2)
                        diff = (max_target - p) / 3
                        target1 = round(p + diff, 2)
                        target2 = round(p + (diff * 2), 2)
                        target3 = round(max_target, 2)
                        stop_loss_hard = chart_low
                        stop_loss_fast = round(p - (p - chart_low) * 0.5, 2) if chart_low < p else round(p * 0.99, 2)
                        
                        # حساب العقد الحقيقي للكول
                        opt_label = "CALL"
                        strike_val = calculate_real_strike(t, p, "CALL")
                    else:
                        min_target = chart_low if chart_low < p else round(p * 0.97, 2)
                        diff = (p - min_target) / 3
                        target1 = round(p - diff, 2)
                        target2 = round(p - (diff * 2), 2)
                        target3 = round(min_target, 2)
                        stop_loss_hard = chart_high
                        stop_loss_fast = round(p + (chart_high - p) * 0.5, 2) if chart_high > p else round(p * 1.01, 2)
                        
                        # حساب العقد الحقيقي للبوت
                        opt_label = "PUT"
                        strike_val = calculate_real_strike(t, p, "PUT")

                    expiry_date = get_next_friday()

                    active_trades[t] = {
                        'type': signal_type,
                        't1': target1, 't2': target2, 't3': target3,
                        'sl': stop_loss_fast,
                        't1_hit': False, 't2_hit': False
                    }

                    # ✨ الرسالة الملكية مضاف لها كود العقد الحقيقي الموزون
                    msg = (
                        f"{icon} **رادار عبدالرحمن الشامل**\n"
                        f"📊 **قوة الصفقة:** {confidence}\n"
                        f"───────────────────\n"
                        f"📌 **الـسـهـم:** `{t}`\n"
                        f"🎫 **العقد المقترح:** `{t} {expiry_date} {strike_val} {opt_label}`\n"
                        f"📈 **الإشـارة:** *{signal_type}*\n"
                        f"💰 **سعر السهم الحالي:** `${p}`\n"
                        f"🐋 **فوليوم الكاش:** `{vol_ratio}x`\n"
                        f"───────────────────\n"
                        f"🎯 **الهدف الأول:** `${target1}`\n"
                        f"🎯 **الهدف الثاني:** `${target2}`\n"
                        f"🎯 **الهدف الثالث:** `${target3}`\n"
                        f"───────────────────\n"
                        f"🛑 **وقف قريب:** `${stop_loss_fast}`\n"
                        f"🛑 **وقف رئيسي:** `${stop_loss_hard}`\n"
                        f"───────────────────"
                    )
                    
                    bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                    last_signals[t] = signal_type 
                    time.sleep(2)
        except: continue

def main():
    try: bot.send_message(CHAT_ID, "🦅 **تم تشغيل الرادار الملكي المطور!**\n- حساب تلقائي للسترايكات الحقيقية والتواريخ المطابقة لتطبيق سهم.\n- نظام المتابعة الفورية للأهداف شغال لايف الحين.", parse_mode='Markdown')
    except Exception as e: print(e)
    while True:
        scan_market()
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    main()
