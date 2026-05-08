import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask

app = Flask(__name__)
active_trades = {} # ذاكرة البوت لمتابعة الأهداف

@app.route('/')
def home():
    return "Target Tracker Mode: Active!"

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload)
    except: pass

def start_bot():
    send_message("🎯 <b>تم تفعيل نظام (مراقب الأهداف)!</b>\nسأقوم الآن بصيد الفرص ومتابعتها حتى تحقيق الربح.")
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMZN', 'MSFT', 'META', 'NFLX', 'AMD', 'OXY', 'PLTR', 'BABA']
    
    while True:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='2d', interval='5m')
                if data.empty: continue

                # حساب المؤشرات
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

                # --- ميزة متابعة الأهداف المحققة ---
                if symbol in active_trades:
                    trade = active_trades[symbol]
                    # تحقق من هدف الـ CALL
                    if trade['type'] == 'CALL' and price >= trade['target']:
                        send_message(f"💰 <b>مبروووك! تحقق الهدف في {symbol}</b>\n✅ السعر وصل: ${price:.2f}\n📈 ربح طيب بإذن الله!")
                        del active_trades[symbol]
                    # تحقق من هدف الـ PUT
                    elif trade['type'] == 'PUT' and price <= trade['target']:
                        send_message(f"💰 <b>مبروووك! تحقق الهدف في {symbol}</b>\n✅ السعر وصل: ${price:.2f}\n📉 صيدة موفقة!")
                        del active_trades[symbol]

                # --- رصد الصفقات الجديدة ---
                score = 0
                signal = ""
                if rsi < 52:
                    signal = "CALL"
                    if price <= lower_b: score += 1
                    if rsi < 42: score += 1
                    if macd_line > sig_line: score += 1
                elif rsi > 52:
                    signal = "PUT"
                    if price >= upper_b: score += 1
                    if rsi > 62: score += 1
                    if macd_line < sig_line: score += 1

                if signal and score >= 1:
                    conf = "🔴 ضعيفة" if score == 1 else "🟡 متوسطة" if score == 2 else "🟢 عالية"
                    target_price = upper_b if signal == "CALL" else lower_b
                    
                    # حفظ الصفقة للمتابعة (فقط إذا لم تكن موجودة سابقاً)
                    if symbol not in active_trades:
                        active_trades[symbol] = {'type': signal, 'target': target_price}
                        
                        msg = (f"🎯 <b>تنبيه دخول: {symbol} [{signal}]</b>\n"
                               f"📊 الثقة: {conf}\n\n"
                               f"📍 السعر: ${price:.2f}\n"
                               f"🚀 الهدف المرقب: ${target_price:.2f}")
                        send_message(msg)
            except: pass
            time.sleep(1)
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    start_bot()
