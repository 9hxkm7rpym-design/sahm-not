import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)
active_trades = {}

@app.route('/')
def home():
    return "Ultra-Radar: Active"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload)
    except: pass

def start_bot():
    # رسالة تفعيل مع اختبار بيانات
    send_message("🚀 <b>بدأ الرادار الخارق!</b>\nجاري فحص البيانات الآن...")
    
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'NFLX', 'AMD', 'OXY', 'PLTR']
    
    while True:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                # استخدام فريم دقيقتين لضمان تدفق البيانات بسرعة في ساعة الإغلاق
                data = ticker.history(period='1d', interval='2m') 
                
                if data.empty:
                    print(f"No data for {symbol}")
                    continue

                # حساب المؤشرات الأساسية
                data['RSI'] = ta.rsi(data['Close'], length=14)
                bbands = ta.bbands(data['Close'], length=20, std=2)
                data = data.join(bbands)
                
                price = data['Close'].iloc[-1]
                rsi = data['RSI'].iloc[-1]
                upper_b = data['BBU_20_2.0'].iloc[-1]
                lower_b = data['BBL_20_2.0'].iloc[-1]

                # شرط إرسال "أي شيء" للتأكد من العمل
                signal = ""
                score = 0
                
                if rsi < 55: # نطاق واسع جداً للـ CALL
                    signal = "CALL"
                    if price <= lower_b: score += 2
                    if rsi < 40: score += 1
                else: # نطاق واسع جداً للـ PUT
                    signal = "PUT"
                    if price >= upper_b: score += 2
                    if rsi > 60: score += 1

                if signal:
                    conf = "🟢 عالية" if score >= 2 else "🟡 متوسطة" if score == 1 else "🔴 ضعيفة"
                    target_p = upper_b if signal == "CALL" else lower_b
                    
                    msg = (f"📍 <b>تنبيه مباشر: {symbol}</b>\n"
                           f"اتجاه مقترح: {signal}\n"
                           f"درجة الثقة: {conf}\n"
                           f"السعر: ${price:.2f}")
                    
                    send_message(msg)
                    # ننتظر قليلاً قبل السهم التالي لتجنب الحظر
                    time.sleep(2) 
            except Exception as e:
                print(f"Error: {e}")
            
        time.sleep(30) # فحص كل نصف دقيقة

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
