import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Final Pro Radar: Online"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def start_bot():
    send_message("⚡ <b>تم تفعيل الرادار النهائي!</b>\nسأبدأ بإرسال الصفقات الآن فور توفرها.")
    
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'NFLX', 'AMD', 'OXY', 'PLTR', 'COIN']
    
    while True:
        for symbol in symbols:
            try:
                # فريم 5 دقائق المستقر
                data = yf.download(symbol, period='2d', interval='5m', progress=False)
                
                if data.empty or len(data) < 15: continue

                # حساب المؤشرات
                close_prices = data['Close'].squeeze()
                rsi = ta.rsi(close_prices, length=14).iloc[-1]
                bbands = ta.bbands(close_prices, length=20, std=2)
                
                price = close_prices.iloc[-1]
                upper_b = bbands['BBU_20_2.0'].iloc[-1]
                lower_b = bbands['BBL_20_2.0'].iloc[-1]

                signal = ""
                score = 0
                
                # تحليل CALL
                if rsi < 55:
                    signal = "CALL"
                    if price <= lower_b: score += 2
                    if rsi < 40: score += 1
                
                # تحليل PUT
                elif rsi > 45:
                    signal = "PUT"
                    if price >= upper_b: score += 2
                    if rsi > 60: score += 1

                if signal:
                    conf = "🟢 قوية" if score >= 2 else "🟡 متوسطة" if score == 1 else "🔴 ضعيفة"
                    msg = (f"🎯 <b>{symbol} | {signal}</b>\n"
                           f"📊 الثقة: {conf}\n"
                           f"💰 السعر: ${price:.2f}\n"
                           f"🚀 الهدف: ${upper_b if signal == 'CALL' else lower_b:.2f}")
                    
                    send_message(msg)
                    time.sleep(1) # سرعة في التنقل
            except:
                continue 
        
        time.sleep(30) # فحص متكرر كل نصف دقيقة

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
