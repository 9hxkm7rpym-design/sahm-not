import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Active: Monitoring RSI + Company News!"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except:
        pass

def get_company_news(symbol):
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news[:2] # سحب آخر خبرين فقط
        news_text = "\n<b>📰 آخر الأخبار:</b>"
        for item in news:
            title = item.get('title', 'لا يوجد عنوان')
            link = item.get('link', '#')
            news_text += f"\n• <a href='{link}'>{title}</a>"
        return news_text
    except:
        return ""

def start_bot():
    send_message("🚀 <b>تم تحديث البوت بنجاح!</b>\nجاري مراقبة المؤشرات والأخبار لـ 12 شركة قيادية.")
    
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'GOOGL', 'NFLX', 'OXY', 'BLDP']
    
    while True:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='2d', interval='5m')
                
                if not data.empty:
                    data['RSI'] = ta.rsi(data['Close'], length=14)
                    current_rsi = data['RSI'].iloc[-1]
                    current_price = data['Close'].iloc[-1]
                    
                    # التنبيه تحت RSI 50 عشان يعطيك تنبيهات أكثر في البداية
                    if current_rsi < 50:
                        news = get_company_news(symbol)
                        msg = (f"🎯 <b>فرصة صيد: {symbol}</b>\n"
                               f"💰 السعر الحالي: ${current_price:.2f}\n"
                               f"📉 مؤشر RSI: {current_rsi:.2f}\n"
                               f"{news}\n\n"
                               f"🔗 <a href='https://tradingview.com/symbols/{symbol}'>تحليل الشارت</a>")
                        send_message(msg)
            except Exception as e:
                print(f"Error with {symbol}: {e}")
            
            time.sleep(2) # راحة بسيطة بين كل شركة وشركة عشان الحظر
            
        time.sleep(300) # فحص شامل كل 5 دقائق

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
