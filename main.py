import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import threading

# --- إعدادات البوت ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RENDER_URL = "https://sahm-not.onrender.com" # ضع رابط موقعك هنا

# قائمة الأسهم المحدثة
WATCHLIST = ['NVDA', 'META', 'TSLA', 'AAPL', 'MSFT', 'OXY', 'SPY', 'AMD']

# ذاكرة البوت لمنع التكرار وحفظ نتائج اليوم
last_alerts = {}
daily_log = []

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}&parse_mode=Markdown"
    try:
        requests.get(url)
    except:
        print("Error sending message")

def get_signal(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='5m', progress=False)
        if data.empty: return None
        
        # حساب المؤشرات
        close = data['Close'].iloc[-1]
        sma = data['Close'].rolling(window=10).mean().iloc[-1]
        
        # حساب RSI بسيط
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        signal = "SIDEWAYS"
        if close > sma and rsi < 70: signal = "CALL 🟢"
        elif close < sma and rsi > 30: signal = "PUT 🔴"
        
        return {
            'price': round(float(close), 2),
            'rsi': round(float(rsi), 1),
            'sma': round(float(sma), 2),
            'signal': signal
        }
    except:
        return None

def analyze_market():
    global daily_log
    for ticker in WATCHLIST:
        analysis = get_signal(ticker)
        if not analysis or analysis['signal'] == "SIDEWAYS": continue

        current_price = analysis['price']
        
        # منع التكرار: إذا كان السعر لم يتغير بأكثر من 0.2% لا ترسل
        if ticker in last_alerts:
            old_price = last_alerts[ticker]
            diff = abs(current_price - old_price) / old_price
            if diff < 0.002: continue 

        last_alerts[ticker] = current_price
        
        # اقتراح السترايك (أقرب رقم صحيح)
        strike = round(current_price)
        if "CALL" in analysis['signal']:
            strike += 1
            emoji = "🚀"
        else:
            strike -= 1
            emoji = "📉"

        msg = (
            f"🤖 *تنبيه قناص الصحراء* {emoji}\n"
            f"📊 السهم: {ticker}\n"
            f"💰 السعر: ${current_price}\n"
            f"📉 RSI: {analysis['rsi']}\n"
            f"-------------------\n"
            f"الاتجاه: {analysis['signal']}\n"
            f"🎯 السترايك المقترح: {strike}\n"
            f"🛡️ الوقف: {round(current_price * 0.99, 2) if 'CALL' in analysis['signal'] else round(current_price * 1.01, 2)}"
        )
        send_message(msg)
        daily_log.append({'time': datetime.now(), 'ticker': ticker, 'price': current_price, 'signal': analysis['signal']})

# وظيفة لإرسال تقرير الإغلاق
def send_daily_report():
    if not daily_log: return
    report = "📊 *تقرير حصاد اليوم يا سلطان* 📊\n\n"
    for item in daily_log[-10:]: # آخر 10 صفقات
        report += f"✅ {item['ticker']} | {item['signal']} عند ${item['price']}\n"
    send_message(report)

# وظيفة منع النوم (Ping)
def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL)
            print("Pinging server to stay awake...")
        except:
            print("Ping failed")
        time.sleep(120) # كل دقيقتين

def main_loop():
    tz = pytz.timezone('Asia/Riyadh')
    report_sent = False
    
    while True:
        now = datetime.now(tz)
        
        # هل السوق مفتوح؟ (4:30 م إلى 11:00 م بتوقيت السعودية)
        if (now.hour == 16 and now.minute >= 30) or (17 <= now.hour < 23):
            analyze_market()
            report_sent = False
        
        # إرسال التقرير الساعة 11:05 م
        if now.hour == 23 and now.minute == 5 and not report_sent:
            send_daily_report()
            report_sent = True
            daily_log.clear() # تصفير السجل ليوم جديد

        time.sleep(60)

if __name__ == "__main__":
    # تشغيل نظام منع النوم في خلفية الكود
    threading.Thread(target=keep_alive, daemon=True).start()
    main_loop()
