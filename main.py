import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Active and Hunting!"

# التوكن الصحيح من صورتك الأخيرة
TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

def start_bot():
    # رسالة تأكيد فورية
    send_message("✅ أبشرك.. تم الربط بنجاح! بوت (صيد الأسهم) شغال الحين ويراقب لك السوق.")
    symbols = ['NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'GOOGL', 'NFLX']
    
    while True:
        for symbol in symbols:
            try:
                data = yf.download(symbol, period='1d', interval='5m', progress=False)
                if not data.empty:
                    data['RSI'] = ta.rsi(data['Close'], length=14)
                    current_rsi = data['RSI'].iloc[-1]
                    # التنبيه إذا الـ RSI تحت 45
                    if current_rsi < 45:
                        msg = f"🚨 فرصة صيد: {symbol}\nمؤشر RSI: {current_rsi:.2f}\nشيك على تطبيق سهم! 📈"
                        send_message(msg)
            except:
                pass
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
