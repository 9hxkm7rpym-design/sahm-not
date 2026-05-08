import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Ultra-Sensitive Mode: Active!"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload)
    except: pass

def start_bot():
    send_message("🔥 <b>تم تفعيل وضع الحساسية القصوى!</b>\nسأرسل لكِ كل الحركات المتاحة مع تحديد درجة الثقة.")
    symbols = [
        'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'NFLX', 
        'AMD', 'GOOGL', 'OXY', 'XOM', 'BA', 'COST', 'PLTR', 'BABA', 'COIN'
    ]
    
    while True:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='2d', interval='5m')
                if data.empty or len(data) < 20: continue

                data['RSI'] = ta.rsi(data['Close'], length=14)
                bbands = ta.bbands(data['Close'], length=20, std=2)
                data = data.join(bbands)
                macd = ta.macd(data['Close'])
                data = data.join(macd)
                
                price = data['Close'].iloc[-1]
                rsi = data['RSI'].iloc[-1]
                upper_b = data['BBU_20_2.0'].iloc[-1]
                lower_b = data['BBL_20_2.0'].iloc[-1]
                macd_line = data['MACD_12_26_9'].iloc[-1]
                sig_line = data['MACDs_12_26_9'].iloc[-1]

                score = 0
                signal = ""
                
                # --- رصد الـ CALL (حساسية مرتفعة جداً) ---
                if rsi < 52: 
                    signal = "CALL"
                    if price <= lower_b: score += 1
                    if rsi < 40: score += 1
                    if macd_line > sig_line: score += 1

                # --- رصد الـ PUT (حساسية مرتفعة جداً) ---
                elif rsi > 52:
                    signal = "PUT"
                    if price >= upper_b: score += 1
                    if rsi > 60: score += 1
                    if macd_line < sig_line: score += 1

                if signal and score >= 1:
                    conf = "🔴 ضعيفة" if score == 1 else "🟡 متوسطة" if score == 2 else "🟢 عالية جداً"
                    msg = (f"🎯 <b>تنبيه صفقة: {symbol} [{signal}]</b>\n"
                           f"📊 <b>درجة الثقة: {conf}</b>\n\n"
                           f"📍 السعر: ${price:.2f}\n"
                           f"🎫 السترايك: ${round(price + 1) if signal == 'CALL' else round(price - 1)}\n"
                           f"🚀 الهدف: ${upper_b if signal == 'CALL' else lower_b:.2f}")
                    
                    send_message(msg + f"\n🔗 <a href='https://tradingview.com/symbols/{symbol}'>الشارت</a>")
                    
            except: pass
            time.sleep(1)
        time.sleep(60) # فحص كل دقيقة لسرعة الاستجابة

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
