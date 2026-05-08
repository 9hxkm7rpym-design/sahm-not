import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home(): 
    return "Transparency-Bot: Active"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=5)
    except: pass

def start_bot():
    send_message("📡 <b>الرادار متصل الآن..</b>\nسأقوم بإرسال الصفقات فور تحقق شروط الـ RSI.")
    
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD']
    
    while True:
        for symbol in symbols:
            try:
                data = yf.download(symbol, period='1d', interval='1m', progress=False)
                
                if data.empty or len(data) < 20:
                    continue

                rsi = ta.rsi(data['Close'], length=14).iloc[-1]
                price = data['Close'].iloc[-1]
                
                # طباعة في اللوج للتأكد من العمل
                print(f"Checking {symbol}: RSI {rsi:.2f}")

                # شروط مرنة للإرسال السريع
                if rsi < 45: # CALL
                    msg = f"🟢 <b>فرصة CALL: {symbol}</b>\n📈 RSI: {int(rsi)}\n💰 السعر: ${price:.2f}"
                    send_message(msg)
                    time.sleep(2)
                elif rsi > 55: # PUT
                    msg = f"🔴 <b>فرصة PUT: {symbol}</b>\n📈 RSI: {int(rsi)}\n💰 السعر: ${price:.2f}"
                    send_message(msg)
                    time.sleep(2)
            except:
                pass
        
        time.sleep(15)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
