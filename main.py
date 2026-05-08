import yfinance as yf
import requests
import time
import pandas_ta as ta
import os
from threading import Thread
from flask import Flask

# سيرفر وهمي لإبقاء البوت صاحي في Render
app = Flask('')
@app.route('/')
def home():
    return "Bot is Hunting!"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# إعداداتك (تأكد من وضع التوكن كاملاً)
TOKEN = "8308789681:AAFLJuVqqQ3J..." 
CHAT_ID = "1068286006"
# أضفت لك BALLARD POWER هنا
stocks = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'OXY', 'BLDP'] 

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params)
    except:
        pass

def check_market():
    send_msg("🚀 **تم تشغيل الرادار المطور!**\nنطاق الصيد: RSI تحت 40")
    while True:
        for symbol in stocks:
            try:
                # سحب بيانات الدقيقة الأخيرة
                df = yf.download(symbol, period='1d', interval='1m', progress=False)
                if not df.empty:
                    df['RSI'] = ta.rsi(df['Close'], length=14)
                    current_rsi = df['RSI'].iloc[-1]
                    current_price = df['Close'].iloc[-1]
                    
                    # --- التعديل هنا: خليناه 40 عشان يعطيك فرص أكثر ---
                    if current_rsi <= 40:
                        msg = f"🔔 **فرصة قريبة!**\n\nالسهم: `{symbol}`\nالسعر الحالي: `{current_price:.2f}$`\nالـ RSI الحالي: `{current_rsi:.2f}`\n\n*السهم في منطقة ارتداد محتملة!*"
                        send_msg(msg)
            except Exception as e:
                print(f"Error: {e}")
        
        time.sleep(300) # فحص كل 5 دقائق

if __name__ == "__main__":
    Thread(target=run_server).start()
    check_market()
