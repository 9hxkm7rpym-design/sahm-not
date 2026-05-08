import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Ultra-Smart Bot: 5m Pulse & Confidence Tiers Active!"

# بيانات التليجرام (تأكدي أن التوكن والـ ID صحيحين)
TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except:
        pass

def start_bot():
    send_message("🛡️ <b>تم تفعيل النسخة النهائية الخارقة!</b>\nالرادار الحساس يعمل الآن بـ 4 مدارس تحليلية ونظام تقييم الثقة.")
    
    # قائمة الشركات الموسعة (30 شركة من الأقوى في السوق)
    symbols = [
        'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'NFLX', 
        'AMD', 'GOOGL', 'OXY', 'XOM', 'CVX', 'BA', 'DIS', 'UNH', 'V', 'JPM', 
        'COST', 'AVGO', 'BLDP', 'PLTR', 'SNOW', 'BABA', 'PYPL', 'INTC', 'MRNA', 'ABNB', 'COIN'
    ]
    
    while True:
        for symbol in symbols:
            try:
                # سحب بيانات فريم 5 دقائق
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='2d', interval='5m')
                
                if data.empty or len(data) < 30: continue

                # 1. حساب الزخم (RSI)
                data['RSI'] = ta.rsi(data['Close'], length=14)
                
                # 2. حساب الموجات (Bollinger Bands)
                bbands = ta.bbands(data['Close'], length=20, std=2)
                data = data.join(bbands)
                
                # 3. حساب الاتجاه (MACD)
                macd = ta.macd(data['Close'])
                data = data.join(macd)
                
                # القيم الحالية
                price = data['Close'].iloc[-1]
                rsi = data['RSI'].iloc[-1]
                upper_b = data['BBU_20_2.0'].iloc[-1]
                lower_b = data['BBL_20_2.0'].iloc[-1]
                macd_line = data['MACD_12_26_9'].iloc[-1]
                sig_line = data['MACDs_12_26_9'].iloc[-1]
                vol_ratio = data['Volume'].iloc[-1] / data['Volume'].mean()

                score = 0
                signal = ""
                
                # --- رصد الـ CALL ---
                if price <= (lower_b * 1.001) or rsi < 50:
                    signal = "CALL"
                    if price <= lower_b: score += 1      # شرط الموجة
                    if rsi < 40: score += 1             # شرط الزخم
                    if macd_line > sig_line: score += 1  # شرط الاتجاه
                    if vol_ratio > 1.3: score += 1       # شرط السيولة

                # --- رصد الـ PUT ---
                elif price >= (upper_b * 0.999) or rsi > 55:
                    signal = "PUT"
                    if price >= upper_b: score += 1      # شرط الموجة
                    if rsi > 65: score += 1             # شرط الزخم
                    if macd_line < sig_line: score += 1  # شرط الاتجاه
                    if vol_ratio > 1.3: score += 1       # شرط السيولة

                # إرسال التنبيه لكل الدرجات (كما طلبتِ)
                if signal and score >= 1:
                    # تحديد نص درجة الثقة
                    if score == 1:
                        confidence = "🔴 ضعيفة (مخاطرة عالية)"
                    elif score == 2:
                        confidence = "🟡 متوسطة (جيدة للمضاربة)"
                    elif score == 3:
                        confidence = "🟢 عالية (فرصة قوية)"
                    else:
                        confidence = "💎 عالية جداً (صيدة ذهبية)"

                    msg = (f"🎯 <b>تنبيه صفقة: {symbol} [{signal}]</b>\n"
                           f"📊 <b>درجة الثقة: {confidence}</b>\n\n"
                           f"📍 السعر: ${price:.2f}\n"
                           f"🎫 السترايك: ${round(price + 1) if signal == 'CALL' else round(price - 1)}\n"
                           f"🎯 الهدف المتوقع: ${upper_b if signal == 'CALL' else lower_b:.2f}\n"
                           f"⚠️ الوقف المقترح: ${lower_b if signal == 'CALL' else upper_b:.2f}")
                    
                    send_message(msg + f"\n\n🔗 <a href='https://tradingview.com/symbols/{symbol}'>افتح الشارت</a>")
                    
            except:
                pass
            time.sleep(1) # لضمان عدم حظر الـ API
            
        time.sleep(180) # يفحص كل 3 دقائق

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
