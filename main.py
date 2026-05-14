import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks

# --- إعدادات سلطان الخاصة ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

# قائمة الأسهم للمراقبة
WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'AMD', 'RBLX', 'SPY', 'QQQ', 'OXY', 'CVX']

def get_signal():
    for t in WATCHLIST:
        try:
            # سحب بيانات 15 يوم (فريم الساعة) لتحليل المحطات السعرية الحقيقية
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=60m&range=15d"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            data = r['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame(data).ffill()
            
            p = round(df['close'].iloc[-1], 2)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['sma20'] = ta.sma(df['close'], length=20)
            
            # --- استخراج الدعوم والمقاومات الحقيقية (find_peaks) ---
            peaks, _ = find_peaks(df['high'], distance=12) 
            troughs, _ = find_peaks(-df['low'], distance=12)
            resistances = sorted(df['high'].iloc[peaks].unique())
            supports = sorted(df['low'].iloc[troughs].unique())

            status = None
            if df['rsi'].iloc[-1] < 45: status = 'CALL'
            elif df['rsi'].iloc[-1] > 55: status = 'PUT'

            if status:
                if status == 'CALL':
                    # أهداف هي مقاومات حقيقية فوق السعر الحالي بمسافة كافية
                    targets = [round(r, 2) for r in resistances if r > p * 1.008]
                    stop = round(supports[-1] if any(s < p for s in supports) else p * 0.98, 2)
                else:
                    # أهداف هي دعوم حقيقية تحت السعر الحالي بمسافة كافية
                    targets = sorted([round(s, 2) for s in supports if s < p * 0.992], reverse=True)
                    stop = round(resistances[0] if any(r > p for r in resistances) else p * 1.02, 2)

                # ضمان وجود 3 أهداف متباعدة في الرسالة
                while len(targets) < 3:
                    diff = 1.015 if status == 'CALL' else 0.985
                    targets.append(round(targets[-1] * diff, 2) if targets else p)

                # --- تنسيق الرسالة النهائي ---
                msg = (f"🤖 **رسالة من البوت الآلي**\n"
                       f"📊 إشارة تداول: `{t}`\n"
                       f"💰 السعر الحالي: `${p}`\n"
                       f"📈 RSI: {round(df['rsi'].iloc[-1])} | SMA: {round(df['sma20'].iloc[-1], 1)}\n"
                       f"------------------------------\n"
                       f"الاتجاه: {'كول 🟢 CALL' if status == 'CALL' else 'بوت 🔴 PUT'}\n"
                       f"🕒 الصلاحية: Intraday\n\n"
                       f"⚙️ **خطة التنفيذ (محطات الشارت):**\n"
                       f"🔹 منطقة الدخول: `{p}`\n"
                       f"🔹 مستوى الوقف: `{stop}`\n"
                       f"🎯 هدف 1: `{targets[0]}`\n"
                       f"🎯 هدف 2: `{targets[1]}`\n"
                       f"🎯 هدف 3: `{targets[2]}`\n\n"
                       f"📋 **العقد المقترح:**\n"
                       f"Strike: {round(targets[0])} | {'🟢' if status == 'CALL' else '🔴'}")
                
                bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                time.sleep(2) 
        except Exception as e:
            print(f"Error in {t}: {e}")
            continue

if __name__ == "__main__":
    print("✅ تم تشغيل رادار سلطان بنجاح...")
    while True:
        get_signal()
        time.sleep(600) # فحص كل 10 دقائق
