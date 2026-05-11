import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import threading
from flask import Flask # رجعناه بس عشان نرضي Render

# --- إعدادات البوت ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RENDER_URL = "https://sahm-not.onrender.com" 

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running!" # هذي الرسالة اللي تطلع لـ Render عشان ما يطفي

# قائمة الأسهم
WATCHLIST = ['NVDA', 'META', 'TSLA', 'AAPL', 'MSFT', 'OXY', 'SPY', 'AMD']
last_alerts = {}
daily_log = []

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}&parse_mode=Markdown"
    try: requests.get(url)
    except: print("Error sending message")

def get_signal(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='5m', progress=False)
        if data.empty: return None
        close = data['Close'].iloc[-1]
        sma = data['Close'].rolling(window=10).mean().iloc[-1]
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        signal = "SIDEWAYS"
        if close > sma and rsi < 70: signal = "CALL 🟢"
        elif close < sma and rsi > 30: signal = "PUT 🔴"
        return {'price': round(float(close), 2), 'rsi': round(float(rsi), 1), 'signal': signal}
    except: return None

def analyze_market():
    global daily_log
    while True:
        tz = pytz.timezone('Asia/Riyadh')
        now = datetime.now(tz)
        if (now.hour == 16 and now.minute >= 30) or (17 <= now.hour < 23):
            for ticker in WATCHLIST:
                analysis = get_signal(ticker)
                if not analysis or analysis['signal'] == "SIDEWAYS": continue
                current_price = analysis['price']
                if ticker in last_alerts:
                    if abs(current_price - last_alerts[ticker]) / last_alerts[ticker] < 0.002: continue 
                last_alerts[ticker] = current_price
                strike = round(current_price) + (1 if "CALL" in analysis['signal'] else -1)
                msg = f"🤖 *قناص الصحراء V2* 🦅\n📊 {ticker} | ${current_price}\n📈 RSI: {analysis['rsi']}\n🎯 سترايك: {strike}\nالاتجاه: {analysis['signal']}"
                send_message(msg)
                daily_log.append({'time': now, 'ticker': ticker, 'price': current_price, 'signal': analysis['signal']})
        
        if now.hour == 23 and now.minute == 5:
            if daily_log:
                report = "📊 *حصاد اليوم يا سلطان* 📊\n" + "\n".join([f"✅ {i['ticker']} | {i['signal']}" for i in daily_log[-10:]])
                send_message(report)
                daily_log.clear()
        time.sleep(60)

def keep_alive():
    while True:
        try: requests.get(RENDER_URL)
        except: pass
        time.sleep(120)

if __name__ == "__main__":
    # تشغيل التحليل ومنع النوم في خيوط منفصلة
    threading.Thread(target=analyze_market, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    # تشغيل Flask على البورت اللي يطلبه Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
