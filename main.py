import yfinance as yf
import requests
import time
import pandas_ta as ta
import os
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Server is Running"

def run():
    app.run(host='0.0.0.0', port=10000)

# إعدادات تليجرام
TOKEN = "6828224522:AAEYH892fA-BfS6h6x6r1-2T_f6rY7f6rY7" 
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload)
    except:
        pass

def start_bot():
    # رسالة ترحيبية بالإنجليزية للتأكد من الربط
    send_message("Bot Started Successfully!")
    symbols = ['NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'GOOGL', 'NFLX']
    
    while True:
        for symbol in symbols:
            try:
                data = yf.download(symbol, period='1d', interval='5m', progress=False)
                if not data.empty:
                    data['RSI'] = ta.rsi(data['Close'], length=14)
                    current_rsi = data['RSI'].iloc[-1]
                    
                    if current_rsi < 45:
                        msg = f"Alert: {symbol}\nRSI: {current_rsi:.2f}\nCheck your Sahm app!"
                        send_message(msg)
            except:
                pass
        time.sleep(300)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    start_bot()
