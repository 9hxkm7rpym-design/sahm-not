import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Emergency Mode: Active"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def start_bot():
    send_message("🚨 <b>وضع الطوارئ (المطاردة القصوى) يعمل الآن!</b>\nلن أصمت بعد الآن.. سأرسل لكِ كل نبضة في السوق.")
    
    # قائمة مركزة لأكثر الأسهم حركة الآن
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD', 'MSFT', 'AMZN', 'META', 'NFLX']
    
    while True:
        for symbol in symbols:
            try:
                # سحب بيانات 5 دقائق بأسرع طريقة ممكنة
                data = yf.download(symbol, period='1d', interval='5m', progress=False)
                if data.empty: continue

                # تبسيط الحسابات لضمان السرعة وعدم التعليق
                price = data['Close'].iloc[-1]
                rsi = ta.rsi(data['Close'], length=14).iloc[-1]
                
                # حساب بولنجر سريع
                std = data['Close'].rolling(20).std().iloc[-1]
                ma = data['Close'].rolling(20).mean().iloc[-1]
                upper_b = ma + (std * 2)
                lower_b = ma - (std * 2)

                signal = ""
                score = 0
                
                # --- شروط "هجومية" جداً ---
                if rsi < 50: # CALL لو السهم فيه أي مجال صعود
                    signal = "CALL"
                    if price <= lower_b: score += 2
                    if rsi < 40: score += 1
                elif rsi >= 50: # PUT لو السهم بدأ يضعف
                    signal = "PUT"
                    if price >= upper_b: score += 2
                    if rsi > 60: score += 1

                if signal:
                    # تقييم الثقة
                    if score >= 2: conf = "🟢 قوية"
                    elif score == 1: conf = "🟡 متوسطة"
                    else: conf = "🔴 ضعيفة جداً"

                    msg = (f"🔥 <b>{symbol} | {signal}</b>\n"
                           f"📊 الدرجة: {conf}\n"
                           f"💰 السعر: ${price:.2f}\n"
                           f"🧭 RSI: {int(rsi)}")
                    
                    send_message(msg)
                    time.sleep(1) # سرعة المسح
            except: pass
        
        time.sleep(15) # يفحص كل 15 ثانية فقط! (سرعة جنونية)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
