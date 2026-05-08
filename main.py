import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Confidence System Active!"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload)
    except: pass

def start_bot():
    send_message("🛡️ <b>تم تفعيل نظام قياس الثقة!</b>\nسأقوم الآن بتقييم كل صفقة بناءً على توافق 4 مدارس تحليلية.")
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'NFLX', 'AMD', 'OXY', 'PLTR']
    
    while True:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='5d', interval='5m')
                if data.empty: continue

                # حساب المؤشرات
                bbands = ta.bbands(data['Close'], length=20, std=2)
                data = data.join(bbands)
                macd = ta.macd(data['Close'])
                data = data.join(macd)
                data['RSI'] = ta.rsi(data['Close'], length=14)
                
                price = data['Close'].iloc[-1]
                rsi = data['RSI'].iloc[-1]
                macd_line = data['MACD_12_26_9'].iloc[-1]
                signal_line = data['MACDs_12_26_9'].iloc[-1]
                upper_b = data['BBU_20_2.0'].iloc[-1]
                lower_b = data['BBL_20_2.0'].iloc[-1]
                vol_ratio = data['Volume'].iloc[-1] / data['Volume'].mean()

                score = 0
                signal = ""
                
                # --- تقييم الـ CALL ---
                if price <= lower_b or rsi < 45:
                    signal = "CALL"
                    if price <= lower_b: score += 1
                    if rsi < 40: score += 1
                    if macd_line > signal_line: score += 1
                    if vol_ratio > 1.2: score += 1

                # --- تقييم الـ PUT ---
                elif price >= upper_b or rsi > 60:
                    signal = "PUT"
                    if price >= upper_b: score += 1
                    if rsi > 65: score += 1
                    if macd_line < signal_line: score += 1
                    if vol_ratio > 1.2: score += 1

                if signal and score >= 2: # نرسل فقط إذا فيه مدرستين على الأقل اتفقوا
                    confidence = "🔴 ضعيفة" if score == 2 else "🟡 متوسطة" if score == 3 else "🟢 عالية جداً"
                    
                    msg = (f"🎯 <b>صفقة جديدة: {symbol} [{signal}]</b>\n"
                           f"📊 <b>درجة الثقة: {confidence}</b>\n\n"
                           f"📍 السعر: ${price:.2f}\n"
                           f"🎫 السترايك: ${round(price + 1) if signal == 'CALL' else round(price - 1)}\n"
                           f"🎯 الهدف: ${upper_b if signal == 'CALL' else lower_b:.2f}\n"
                           f"⚠️ الوقف: ${lower_b if signal == 'CALL' else upper_b:.2f}")
                    
                    send_message(msg + f"\n\n🔗 <a href='https://tradingview.com/symbols/{symbol}'>افتح الشارت</a>")
            except: pass
            time.sleep(1)
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
