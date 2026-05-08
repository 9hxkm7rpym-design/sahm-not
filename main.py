import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Ultra-Pro Analyzer: Online"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def start_bot():
    send_message("💎 <b>تم تفعيل (المحلل الأسطوري)!</b>\nسأجمع لكِ بين دقة التحليل وكثرة التنبيهات.")
    
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD', 'AMZN', 'MSFT', 'COIN', 'PLTR']
    
    while True:
        for symbol in symbols:
            try:
                # بيانات دقيقة واحدة لأقصى دقة في التوقيت
                data = yf.download(symbol, period='1d', interval='1m', progress=False)
                if data.empty: continue

                # مدرسة RSI
                rsi = ta.rsi(data['Close'], length=14).iloc[-1]
                # مدرسة البولنجر
                bbands = ta.bbands(data['Close'], length=20, std=2)
                # مدرسة المتوسطات
                ma_fast = data['Close'].rolling(5).mean().iloc[-1]
                ma_slow = data['Close'].rolling(20).mean().iloc[-1]

                price = data['Close'].iloc[-1]
                upper_b = bbands['BBU_20_2.0'].iloc[-1]
                lower_b = bbands['BBL_20_2.0'].iloc[-1]

                # --- نظام النقاط الذهبي ---
                score = 0
                signal = ""
                
                # تحليل CALL
                if price < ma_fast or rsi < 50:
                    signal = "CALL 🟢"
                    if rsi < 40: score += 1
                    if price <= lower_b: score += 1
                    if ma_fast > ma_slow: score += 1
                
                # تحليل PUT
                else:
                    signal = "PUT 🔴"
                    if rsi > 60: score += 1
                    if price >= upper_b: score += 1
                    if ma_fast < ma_slow: score += 1

                # إرسال التنبيه (أي شيء فوق الصفر يرسله)
                conf = "🔥 قوية جداً" if score >= 2 else "🟡 جيدة" if score == 1 else "⚪️ ضعيفة/مضاربة"
                
                msg = (f"🚀 <b>{symbol}</b> | {signal}\n"
                       f"📊 التحليل: {conf}\n"
                       f"💰 السعر: ${price:.2f}\n"
                       f"📍 الهدف: ${upper_b if 'CALL' in signal else lower_b:.2f}")
                
                send_message(msg)
                time.sleep(1)
            except: pass
        time.sleep(15)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
