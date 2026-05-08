import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Scalper Bot: Entry, Exit, and Strikes are Active!"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload)
    except: pass

def start_bot():
    send_message("🛡️ <b>نظام إدارة الصفقات نشط!</b>\nسأعطيكِ الأهداف، السترايك، ونقطة الخروج الإجبارية.")
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META']
    
    while True:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='5d', interval='5m')
                
                if not data.empty:
                    data['RSI'] = ta.rsi(data['Close'], length=14)
                    price = data['Close'].iloc[-1]
                    rsi = data['RSI'].iloc[-1]
                    vol = data['Volume'].iloc[-1]
                    avg_vol = data['Volume'].mean()
                    
                    # تحليل مستويات الشارت (القمم والقيعان)
                    resistance = data['High'].max()
                    support = data['Low'].min()
                    
                    msg = ""
                    # --- سيناريو الـ CALL ---
                    if rsi < 45:
                        strike = round(price + (price * 0.01))
                        stop_loss = support * 0.995 # خروج إذا كسر الدعم بـ 0.5%
                        msg = (f"🟢 <b>صفقة مضاربة: {symbol} [CALL]</b>\n"
                               f"🔹 <b>سعر الدخول الحالي:</b> ${price:.2f}\n"
                               f"🎫 <b>السترايك المقترح:</b> ${strike}\n\n"
                               f"🎯 <b>الأهداف:</b> ${price * 1.01:.2f} ثم ${resistance:.2f}\n"
                               f"⚠️ <b>نقطة الخروج (إلزامي):</b> إذا كسر ${stop_loss:.2f}\n\n"
                               f"💡 <i>ملاحظة: إذا نزل السعر تحت الخروج، العقد بيفقد قيمته بسرعة، اطلعي فوراً!</i>")

                    # --- سيناريو الـ PUT ---
                    elif rsi > 65:
                        strike = round(price - (price * 0.01))
                        stop_loss = resistance * 1.005 # خروج إذا تجاوز المقاومة بـ 0.5%
                        msg = (f"🔴 <b>صفقة مضاربة: {symbol} [PUT]</b>\n"
                               f"🔹 <b>سعر الدخول الحالي:</b> ${price:.2f}\n"
                               f"🎫 <b>السترايك المقترح:</b> ${strike}\n\n"
                               f"🎯 <b>الأهداف:</b> ${price * 0.99:.2f} ثم ${support:.2f}\n"
                               f"⚠️ <b>نقطة الخروج (إلزامي):</b> إذا تجاوز ${stop_loss:.2f}\n\n"
                               f"💡 <i>ملاحظة: تجاوز السعر لهذه النقطة يعني استمرار الصعود وضياع عقد البوت.</i>")

                    if msg:
                        # إضافة حالة السيولة في نهاية الرسالة
                        vol_tag = "✅ سيولة تدعم الحركة" if vol > avg_vol else "⚪ سيولة ضعيفة"
                        msg += f"\n\n📊 <b>حالة السيولة:</b> {vol_tag}\n🔗 <a href='https://tradingview.com/symbols/{symbol}'>الشارت</a>"
                        send_message(msg)
            except: pass
            time.sleep(2)
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
