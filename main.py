import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات منظومة عبدالرحمن الفورية النظيفة ---
TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "رادار عبدالرحمن الفوري الصاحي شغال لايف 🦅🔥"

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
    """سحب البيانات الحية اللحظية بدون كاش أو تعليق"""
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

def check_spy_live():
    """معرفة اتجاه السوق العام حالياً"""
    df_spy = get_live_data('SPY')
    if df_spy is None or len(df_spy) < 10: return "NEUTRAL"
    macd = ta.macd(df_spy['close'], fast=12, slow=26, signal=9)
    if macd is None: return "NEUTRAL"
    return "BULLISH" if macd['MACD_12_26_9'].iloc[-1] > macd['MACDs_12_26_9'].iloc[-1] else "BEARISH"

def scan_market():
    global last_signals
    spy_status = check_spy_live()
    
    for t in WATCHLIST:
        try:
            df = get_live_data(t)
            if df is None or len(df) < 15: continue

            # الحسابات الفنية الحية الفورية
            macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
            df['rsi'] = ta.rsi(df['close'], length=14)
            if macd_df is None or df['rsi'].empty: continue

            p = round(df['close'].iloc[-1], 2)
            rsi_v = round(df['rsi'].iloc[-1], 1)
            macd_line = macd_df['MACD_12_26_9'].iloc[-1]
            macd_signal = macd_df['MACDs_12_26_9'].iloc[-1]

            # قياس السيولة الحقيقية اللحظية مقارنة بمتوسط الشموع القريبة
            avg_vol = df['volume'].tail(10).mean()
            current_vol = df['volume'].iloc[-1]
            vol_ratio = round(current_vol / avg_vol, 1) if avg_vol > 0 else 1.0

            # الدعم والمقاومة اللحظية الفورية
            resistance = round(df['high'].tail(15).max(), 2)
            support = round(df['low'].tail(15).min(), 2)

            send_signal = False
            signal_type = ""

            # شرط التقاطع اللحظي الأساسي لغزارة الفرص
            if macd_line > macd_signal:
                signal_type = "CALL 🟢"
                send_signal = True
            elif macd_line < macd_signal:
                signal_type = "PUT 🔴"
                send_signal = True

            if send_signal:
                signal_key = f"{t}_{signal_type}"
                if last_signals.get(t) != signal_type: # يرسل فقط عند تغير الإشارة منعاً للتكرار
                    
                    # الفرز الثلاثي الذكي لمستوى الثقة بناءً على السيولة اللحظية الحقيقية والسوق
                    if vol_ratio >= 1.5 and ((signal_type == "CALL 🟢" and spy_status == "BULLISH") or (signal_type == "PUT 🔴" and spy_status == "BEARISH")):
                        confidence = "عــالــيــة جــداً 🟩"
                        tag = "💎 [دخول كاش الحيتان SMC]"
                        analysis = "توافق كامل ومثالي! سيولة حيتان قوية متدفقة لايف، واتجاه السوق العام يدعم الحركة تماماً."
                    elif vol_ratio >= 1.1:
                        confidence = "متوسطة 🟨"
                        tag = "⚡️ [حركة مضاربية سريعة]"
                        analysis = "زخم فني جيد متوفر على السهم حالياً، والسيولة تعتبر ضمن المعدل الطبيعي الآمن."
                    else:
                        confidence = "ضعيفة 🟥"
                        tag = "⚠️ [تنبيه مخاطرة]"
                        analysis = "السيولة اللحظية ميتة أو ضعيفة جداً، والدخول في هذه المنطقة يعتبر عالي المخاطرة."

                    msg = (
                        f"{tag} **رادار عبدالرحمن الصاحي للسيولة الفورية**\n\n"
                        f"🎯 **نسبة النجاح المتوقعة:** {confidence}\n"
                        f"📌 **السهم المستهدف:** {t}\n"
                        f"📈 **إشارة الأوبشن:** {signal_type}\n"
                        f"💰 **السعر الحالي لايف:** ${p}\n"
                        f"----------------------------------\n"
                        f"🔍 **تحليل السيولة والميزان:**\n{analysis}\n\n"
                        f"📊 **معدل تدفق الكاش الحالي:** {vol_ratio}x\n"
                        f"🎯 **الهدف اللحظي المتوقع:** ${resistance if signal_type == 'CALL 🟢' else support}\n"
                        f"🛑 **وقف الخسارة اللحظي:** ${support if signal_type == 'CALL 🟢' else resistance}\n"
                        f"📉 **حالة السوق العام SPY:** {spy_status}\n"
                        f"----------------------------------"
                    )
                    bot.send_message(CHAT_ID, msg)
                    last_signals[t] = signal_type
                    time.sleep(2)
        except:
            continue

def main():
    try:
        bot.send_message(CHAT_ID, "🦅 تم تشغيل المنظومة النظيفة الصاحية بنجاح!\n- الكود الحين يسحب البيانات الفورية لايف بدون كاش.\n- الصفقات بتجيك الحين بأسعارها الحقيقية تماماً.")
    except Exception as e:
        print(e)

    while True:
        scan_market()
        time.sleep(180) # فحص مستمر كل 3 دقائق للسيولة الحية

if __name__ == "__main__":
    Thread(target=run_flask).start()
    main()
