
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
    return "Bot is Running"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# إعداداتك الخاصة
TOKEN = "8308789681:AAFLJuVqqQ3JmY7v7p_GfG6W7W7W7W7W7"
CHAT_ID = "1068286006"
stocks = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'OXY', 'BLDP']

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params)
    except:
        pass

def check_market():
    # تأخير بسيط لتجنب حظر البيانات (Rate Limit)
    time.sleep(10)
    send_msg("✅ البوت اشتغل تمام وبدأ يراقب الفرص!")
    while True:
        for symbol in stocks:
            try:
                df = yf.download(symbol, period='1d', interval='1m', progress=False)
                if not df.empty:
                    df['RSI'] = ta.rsi(df['Close'], length=14)
                    current_rsi = df['RSI'].iloc[-1]
                    current_price = df['Close'].iloc[-1]
                    if current_rsi <= 45:
                        send_msg(f"🟢 فرصة: {symbol}\nالسعر: {current_price:.2f}\nRSI: {current_rsi:.2f}")
                time.sleep(2) # انتظار بين كل سهم وسهم عشان ما ننحظر
            except:
                continue
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=run_server).start()
    check_market()
