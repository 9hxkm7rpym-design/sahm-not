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
    return "Open Radar Mode: Sending All Tiers!"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload)
    except: pass

def start_bot():
    send_message("🔓 <b>تم تفعيل (الرادار المفتوح)</b>\nسأرسل لكِ كل الحركات الآن، القوية والضعيفة.")
    symbols = [
        'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 
        'NFLX', 'AMD', 'OXY', 'PLTR', 'BABA', 'COIN', 'GOOGL'
    ]
    
    while True:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='2d', interval='5m')
                if data.empty: continue

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

                # --- مراقبة الأهداف المحققة ---
                if symbol in active_trades:
                    trade = active_trades[symbol]
                    if (trade['type'] == 'CALL' and price >= trade['target']) or \
                       (trade['type'] == 'PUT' and price <= trade['target']):
                        send_message(f"💰 <b>تحقق الهدف في {symbol}!</b>\nالسعر الحالي: ${price:.2f}")
                        del active_trades[symbol]

                # --- رصد كل أنواع الصفقات (حتى الضعيفة) ---
                score = 0
                signal = ""
                
                # شرط الدخول صار "واسع" جداً لإرسال كل شيء
                if rsi < 55: # أي ميل للصعود
                    signal = "CALL"
                    if price <= lower_b: score += 1
                    if rsi < 40: score += 2 # ثقة أعلى لو التشبع قوي
                    if macd_line > sig_line: score += 1
                elif rsi > 45: # أي ميل للهبوط
                    signal = "PUT"
                    if price >= upper_b: score += 1
                    if rsi > 60: score += 2
                    if macd_line < sig_line: score += 1

                if signal:
                    # تصنيف الثقة بناءً على النقاط
                    if score <= 1:
                        conf = "🔴 ضعيفة (للمغامرة فقط)"
                    elif score == 2:
                        conf = "🟡 متوسطة (فرصة جيدة)"
                    else:
                        conf = "🟢 عالية جداً (صيدة ذهبية)"

                    if symbol not in active_trades or score >= 3:
                        target_p = upper_b if signal == "CALL" else lower_b
                        active_trades[symbol] = {'type': signal, 'target': target_p}
                        
                        msg = (f"🎯 <b>تنبيه فرصة: {symbol} [{signal}]</b>\n"
                               f"📊 درجة الثقة: {conf}\n\n"
                               f"📍 السعر الحالي: ${price:.2f}\n"
                               f"🚀 الهدف: ${target_p:.2f}")
                        send_message(msg)
            except: pass
            time.sleep(0.5) # سرعة مسح عالية
        time.sleep(30) # راحة قصيرة جداً

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
