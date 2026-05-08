import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home(): return "Final-Stable-Bot: Active"

# --- الإعدادات ---
TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except: pass

def start_bot():
    send_message("✅ <b>تم تحديث البوت للنسخة النهائية المستقرة.</b>\nسأبدأ بجلب الأخبار والبحث عن صفقات قوية.")
    
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'OXY']
    last_news_time = 0

    while True:
        # 1. قسم جلب الأخبار (يشتغل حتى لو السوق مقفل)
        if time.time() - last_news_time > 3600: # كل ساعة خبر
            try:
                news_data = yf.Ticker("SPY").news[:2]
                for item in news_data:
                    send_message(f"🌍 <b>خبر عاجل:</b>\n{item['title']}\n🔗 <a href='{item['link']}'>المصدر</a>")
                last_news_time = time.time()
            except: pass

        # 2. قسم الصفقات
        for symbol in symbols:
            try:
                df = yf.download(symbol, period='1d', interval='1m', progress=False)
                if df.empty: continue

                rsi = ta.rsi(df['Close'], length=14).iloc[-1]
                price = df['Close'].iloc[-1]
                
                # تقييم قوة الصفقة
                signal = ""
                quality = ""
                if rsi < 35: 
                    signal = "CALL 🟢"
                    quality = "🔥 قوة الصفقة: عالية جداً" if rsi < 30 else "🟡 قوة الصفقة: متوسطة"
                elif rsi > 65:
                    signal = "PUT 🔴"
                    quality = "🔥 قوة الصفقة: عالية جداً" if rsi > 70 else "🟡 قوة الصفقة: متوسطة"

                if signal:
                    msg = (f"🎯 <b>صيدة جديدة: {symbol}</b>\n"
                           f"--------------------------\n"
                           f"📍 النوع: {signal}\n"
                           f"📊 {quality}\n"
                           f"💰 السعر: ${price:.2f}\n"
                           f"📈 RSI: {int(rsi)}\n"
                           f"🔗 <a href='https://www.tradingview.com/chart/?symbol={symbol}'>الشارت</a>")
                    send_message(msg)
                    time.sleep(5)
            except: pass
        
        time.sleep(30)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
