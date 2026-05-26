import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os
from datetime import datetime, timedelta, timezone  # أضفنا timezone هنا للحل النهائي

# --- منظومة عبادي المتكاملة للتداول المباشر والإحصاء المسائي ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبادي المباشر شغال 24 ساعة بـ فلاتر الثقة، الأخبار، والتقرير الإحصائي! 🦅🔥"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

WATCHLIST = [
    'AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 
    'OXY', 'MSFT', 'GOOGL', 'META', 'AVGO', 'ASML', 'ADBE', 'CRM', 'PANW', 
    'SHOP', 'COST', 'SNAP', 'CVX', 'PLTR', 'XPEV', 'SOFI', 'F', 'PFE', 'AAL'
]

trade_counter = 0
active_signals = {}

# --- عدادات كشف الحساب اليومي (إحصائيات عبادي) ---
daily_stats = {
    'success_total': 0,
    'failed_total': 0,
    'elite_success': 0,
    'elite_failed': 0,
    'mid_success': 0,
    'mid_failed': 0,
    'low_success': 0,
    'low_failed': 0,
    'report_sent_today': False
}

def get_next_friday():
    today = datetime.now()
    days_ahead = 4 - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_friday = today + timedelta(days_ahead)
    return next_friday.strftime('%d%b%y').upper()

def calculate_real_strike(ticker, current_price, option_type):
    if ticker in ['NVDA', 'TSLA', 'MSFT', 'META', 'AVGO', 'ASML']:
        interval = 2.5 if current_price < 200 else 5.0
    elif ticker in ['AAPL', 'AMD', 'AMZN', 'CRM', 'ADBE', 'COST', 'PANW', 'OXY', 'CVX']:
        interval = 1.0 if current_price < 100 else 2.5
    else:
        interval = 0.5 if current_price < 20 else 1.0
    base = round(current_price / interval) * interval
    if option_type == "CALL":
        strike = base + interval if base <= current_price else base
    else:
        strike = base - interval if base >= current_price else base
    return int(strike) if strike % 1 == 0 else round(strike, 2)

def get_live_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=15m&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=10).json()
        result = r['chart']['result'][0]
        df = pd.DataFrame(result['indicators']['quote'][0])
        df['close'] = df['close'].ffill().bfill()
        df['high'] = df['high'].ffill().bfill()
        df['low'] = df['low'].ffill().bfill()
        df['volume'] = df['volume'].ffill().bfill()
        return df
    except: return None

def get_latest_news(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5).json()
        if 'news' in r and len(r['news']) > 0:
            latest = r['news'][0]
            title = latest.get('title', 'لا توجد تفاصيل للعنوان')
            pub_time = latest.get('providerPublishTime', 0)
            time_str = datetime.fromtimestamp(pub_time).strftime('%I:%M %p') if pub_time else "الآن"
            return f"🔹 {title} ({time_str})"
    except: pass
    return "🔹 لم يتم العثور على أخبار عاجلة حالياً."

def build_message_text(trade_id, ticker, signal_type, current_price, vol_ratio, adx_val, score, t1, t2, t3, sl_fast, news_txt, status_text=""):
    if score == 4: confidence = "قوية جداً (النخبة 🟩)"
    elif score == 3: confidence = "متوسطة الارتداد 🟨"
    else: confidence = "ضعيفة / تذبذب عرضي 🟥"

    expiry_date = get_next_friday()
    opt_label = "CALL" if "CALL" in signal_type else "PUT"
    strike_val = calculate_real_strike(ticker, current_price, opt_label)

    header = f"{status_text}\n\n" if status_text else f"🚀 **[ صفقة جديدة رقم #{trade_id} ]**\n\n"

    msg = (
        f"{header}"
        f"📊 **درجة الثقة الإجمالية:** {confidence} | `[{score} من 4]`\n"
        f"🔍 **قوة التريند (ADX):** `{round(adx_val, 1)}`\n"
        f"🐋 **فوليوم كاش الحيتان:** `{vol_ratio}x`\n"
        f"───────────────────\n"
        f"📌 **الـسـهـم:** `{ticker}`\n"
        f"📊 **الإتـجـاه:** *{signal_type}*\n"
        f"💰 **سعر السهم الحالي:** `${current_price}`\n"
        f"───────────────────\n"
        f"🎫 **بـيـانـات الـعـقـد (انسخه لـ سهْم)**\n"
        f"`{ticker} {expiry_date} {strike_val} {opt_label}`\n"
        f"───────────────────\n"
        f"🎯 **الـمـسـتـهـدفـات (دعوم ومقاومات الشارت)**\n"
        f"• 🔹 الهدف الأول: `${t1}`\n"
        f"• 🔹 الهدف الثاني: `${t2}`\n"
        f"• 🔹 الهدف الثالث: `${t3}`\n"
        f"───────────────────\n"
        f"🛑 **صـمـام الأمـان**\n"
        f"• 🚨 وقف خسارة قريب: `${sl_fast}`\n"
        f"───────────────────\n"
        f"📰 **آخـر أخـبـار الـشـركـة الـلـحـظـيـة:**\n"
        f"*{news_txt}*\n"
        f"───────────────────"
    )
    return msg

def send_daily_report():
    """حساب وإرسال تقرير الأداء اليومي تلقائياً الساعة 12 بالليل"""
    global daily_stats
    total = daily_stats['success_total'] + daily_stats['failed_total']
    win_rate = round((daily_stats['success_total'] / total) * 100, 1) if total > 0 else 0
    
    report = (
        f"📊 **[ تقرير أداء رادار عبادي الختامي لليوم ]**\n"
        f"📅 التاريخ: `{datetime.now().strftime('%Y-%m-%d')}`\n"
        f"───────────────────\n"
        f"✅ **إجمالي الصفقات الناجحة:** `{daily_stats['success_total']} صفقات`\n"
        f"❌ **إجمالي صفقات الوقف (الخاسرة):** `{daily_stats['failed_total']} صفقات`\n"
        f"🎯 **نسبة نجاح المنظومة اليوم الإجمالية:** `{win_rate}%`\n"
        f"───────────────────\n"
        f"💎 **تفاصيل صفقات النخبة [4 من 4] 🟩:**\n"
        f"• نجحت: `{daily_stats['elite_success']}` | ضربت الوقف: `{daily_stats['elite_failed']}`\n\n"
        f"🟨 **تفاصيل الصفقات المتوسطة [3 من 4] 🟨:**\n"
        f"• نجحت: `{daily_stats['mid_success']}` | ضربت الوقف: `{daily_stats['mid_failed']}`\n\n"
        f"🟥 **تفاصيل الصفقات الضعيفة [2 أو أقل] 🟥:**\n"
        f"• نجحت: `{daily_stats['low_success']}` | ضربت الوقف: `{daily_stats['low_failed']}`\n"
        f"───────────────────\n"
        f"🦅 *قفلنا كاش اليوم بنجاح يا عبادي، ونجهز المحفظة لفرص بكره!*"
    )
    try:
        bot.send_message(CHAT_ID, report, parse_mode='Markdown')
        # تصفير العدادات بالكامل لاستقبال اليوم التالي
        for key in daily_stats:
            if isinstance(daily_stats[key], bool): daily_stats[key] = False
            else: daily_stats[key] = 0
    except Exception as e: print(f"Error sending report: {e}")

def check_report_timing():
    """تعديل ذكي لحساب توقيت السعودية بالطريقة الجديدة لتجنب تنبيه بايثون"""
    global daily_stats
    now = datetime.now(timezone.utc) + timedelta(hours=3) # الحل الصافي هنا
    if now.hour == 0 and not daily_stats['report_sent_today']:
        daily_stats['report_sent_today'] = True
        send_daily_report()
    elif now.hour == 1:
        daily_stats['report_sent_today'] = False

def scan_market():
    global active_signals, trade_counter, daily_stats
    
    check_report_timing()
    
    for t in WATCHLIST:
        try:
            df = get_live_data(t)
            if df is None or len(df) < 30: continue

            p = round(df['close'].iloc[-1], 2)

            df['pivot_high'] = df['high'][(df['high'] == df['high'].rolling(11, center=True).max())]
            df['pivot_low'] = df['low'][(df['low'] == df['low'].rolling(11, center=True).min())]
            all_highs = sorted(df['pivot_high'].dropna().unique())
            all_lows = sorted(df['pivot_low'].dropna().unique())

            sti = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
            df['rsi'] = ta.rsi(df['close'], length=14)
            adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
            
            if sti is None or df['rsi'].empty or adx_df is None or adx_df.empty: continue
            
            trend_col = [col for col in sti.columns if 'SUPERTd' in col][0]
            trend_line = sti[trend_col].iloc[-1]
            
            rsi_v = df['rsi'].iloc[-1]
            adx_value = adx_df['ADX_14'].iloc[-1]

            avg_vol = df['volume'].iloc[-11:-1].mean()
            vol_ratio = round(df['volume'].iloc[-2] / avg_vol, 1) if avg_vol > 0 else 1.0

            current_signal_type = ""
            if trend_line == 1 and rsi_v > 50: current_signal_type = "CALL 🟢"
            elif trend_line == -1 and rsi_v < 50: current_signal_type = "PUT 🔴"

            highs_above = [round(h, 2) for h in all_highs if h > p]
            t1_c = highs_above[0] if len(highs_above) > 0 else round(p * 1.01, 2)
            t2_c = highs_above[1] if len(highs_above) > 1 else round(p * 1.02, 2)
            t3_c = highs_above[2] if len(highs_above) > 2 else round(p * 1.04, 2)
            lows_below_c = [round(l, 2) for l in all_lows if l < p]
            sl_fast_c = lows_below_c[-1] if len(lows_below_c) > 0 else round(p * 0.99, 2)

            lows_below = [round(l, 2) for l in all_lows if l < p]
            t1_p = lows_below[-1] if len(lows_below) > 0 else round(p * 0.99, 2)
            t2_p = lows_below[-2] if len(lows_below) > 1 else round(p * 0.98, 2)
            t3_p = lows_below[-3] if len(lows_below) > 2 else round(p * 0.96, 2)
            highs_above_p = [round(h, 2) for h in all_highs if h > p]
            sl_fast_p = highs_above_p[0] if len(highs_above_p) > 0 else round(p * 1.01, 2)

            score = 0
            if trend_line == 1 or trend_line == -1: score += 1
            if current_signal_type and (("CALL" in current_signal_type and rsi_v > 55) or ("PUT" in current_signal_type and rsi_v < 45)): score += 1
            if adx_value >= 20: score += 1
            if vol_ratio >= 1.3: score += 1

            news_headlines = get_latest_news(t)

            if t in active_signals:
                saved_trade = active_signals[t]
                tid = saved_trade['trade_id']
                ts_score = saved_trade['score']
                
                if current_signal_type and current_signal_type != saved_trade['type']:
                    status_txt = f"⚠️ **[ تنبيه: الصفقة رقم #{tid} عكست اتجاهها لايف ]**"
                    if current_signal_type == "CALL 🟢":
                        new_msg = build_message_text(tid, t, current_signal_type, p, vol_ratio, adx_value, score, t1_c, t2_c, t3_c, sl_fast_c, news_headlines, status_txt)
                        saved_trade.update({'type': 'CALL 🟢', 't1': t1_c, 't2': t2_c, 't3': t3_c, 'sl': sl_fast_c, 'hit_1': False, 'hit_2': False})
                    else:
                        new_msg = build_message_text(tid, t, current_signal_type, p, vol_ratio, adx_value, score, t1_p, t2_p, t3_p, sl_fast_p, news_headlines, status_txt)
                        saved_trade.update({'type': 'PUT 🔴', 't1': t1_p, 't2': t2_p, 't3': t3_p, 'sl': sl_fast_p, 'hit_1': False, 'hit_2': False})
                    try: bot.edit_message_text(new_msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                    except: pass
                    continue

                if saved_trade['type'] == "CALL 🟢":
                    if p >= saved_trade['t1'] and not saved_trade['hit_1']:
                        saved_trade['hit_1'] = True
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"🎯 **[ الصفقة رقم #{tid} حققت الهدف الأول ✅ ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                    elif p >= saved_trade['t2'] and not saved_trade['hit_2']:
                        saved_trade['hit_2'] = True
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"🚀 **[ الصفقة رقم #{tid} حققت الهدف الثاني ✅ ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                    elif p >= saved_trade['t3']:
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"👑 **[ الصفقة رقم #{tid} قفلت كل الأهداف بنجاح 💎 ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                        daily_stats['success_total'] += 1
                        if ts_score == 4: daily_stats['elite_success'] += 1
                        elif ts_score == 3: daily_stats['mid_success'] += 1
                        else: daily_stats['low_success'] += 1
                        del active_signals[t]
                    elif p <= saved_trade['sl']:
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"🛑 **[ الصفقة رقم #{tid} ضربت الوقف وحمت المحفظة 🧨 ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                        daily_stats['failed_total'] += 1
                        if ts_score == 4: daily_stats['elite_failed'] += 1
                        elif ts_score == 3: daily_stats['mid_failed'] += 1
                        else: daily_stats['low_failed'] += 1
                        del active_signals[t]

                elif saved_trade['type'] == "PUT 🔴":
                    if p <= saved_trade['t1'] and not saved_trade['hit_1']:
                        saved_trade['hit_1'] = True
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"🎯 **[ الصفقة رقم #{tid} حققت الهدف الأول ✅ ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                    elif p <= saved_trade['t2'] and not saved_trade['hit_2']:
                        saved_trade['hit_2'] = True
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"🚀 **[ الصفقة رقم #{tid} حققت الهدف الثاني ✅ ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                    elif p <= saved_trade['t3']:
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"👑 **[ الصفقة رقم #{tid} قفلت كل الأهداف بنجاح 💎 ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                        daily_stats['success_total'] += 1
                        if ts_score == 4: daily_stats['elite_success'] += 1
                        elif ts_score == 3: daily_stats['mid_success'] += 1
                        else: daily_stats['low_success'] += 1
                        del active_signals[t]
                    elif p >= saved_trade['sl']:
                        msg = build_message_text(tid, t, saved_trade['type'], p, vol_ratio, adx_value, ts_score, saved_trade['t1'], saved_trade['t2'], saved_trade['t3'], saved_trade['sl'], news_headlines, f"🛑 **[ الصفقة رقم #{tid} ضربت الوقف وحمت المحفظة 🧨 ]**")
                        try: bot.edit_message_text(msg, CHAT_ID, saved_trade['message_id'], parse_mode='Markdown')
                        except: pass
                        daily_stats['failed_total'] += 1
                        if ts_score == 4: daily_stats['elite_failed'] += 1
                        elif ts_score == 3: daily_stats['mid_failed'] += 1
                        else: daily_stats['low_failed'] += 1
                        del active_signals[t]

            else:
                if current_signal_type:
                    if len(active_signals) >= 3: continue
                    
                    trade_counter += 1
                    if current_signal_type == "CALL 🟢":
                        msg = build_message_text(trade_counter, t, current_signal_type, p, vol_ratio, adx_value, score, t1_c, t2_c, t3_c, sl_fast_c, news_headlines)
                        sent_msg = bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                        active_signals[t] = {'trade_id': trade_counter, 'message_id': sent_msg.message_id, 'type': 'CALL 🟢', 'score': score, 't1': t1_c, 't2': t2_c, 't3': t3_c, 'sl': sl_fast_c, 'hit_1': False, 'hit_2': False}
                    else:
                        msg = build_message_text(trade_counter, t, current_signal_type, p, vol_ratio, adx_value, score, t1_p, t2_p, t3_p, sl_fast_p, news_headlines)
                        sent_msg = bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                        active_signals[t] = {'trade_id': trade_counter, 'message_id': sent_msg.message_id, 'type': 'PUT 🔴', 'score': score, 't1': t1_p, 't2': t2_p, 't3': t3_p, 'sl': sl_fast_p, 'hit_1': False, 'hit_2': False}
                    time.sleep(2)
        except: continue

def main():
    try: bot.send_message(CHAT_ID, "🦅 **تم تحديث رادار عبادي للنسخة الصافية والمستدامة!**\n\n• تم إصلاح اللوج وإخفاء تنبيهات الوقت.\n• التقرير المسائي المنسق يعمل بدقة الساعة 12 منتصف الليل.\n\nالمنظومة كاملة ومثالية الحين وبانتظار جلسة السوق القادمة! 🎯🔥", parse_mode='Markdown')
    except Exception as e: print(e)
    while True:
        scan_market()
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    main()
