import telebot
import time
import yfinance as yf
from flask import Flask
from threading import Thread

# البيانات اللي تأكدنا منها
TOKEN = "8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

WATCHLIST = ['NVDA', 'TSLA', 'AMZN', 'OXY', 'AAPL', 'MSFT', 'QQQ', '^SPX']

@server.route('/')
def health_check():
    return "Falcon Radar is Running", 200

def scan_markets():
    # رسالة ترحيبية عشان نتأكد إن البوت شبك
    bot.send_message(CHAT_ID, "🚀 تم تحديث الرادار بنظام السحب السريع.. جاري جلب الأسعار")
    
    while True:
        for ticker in WATCHLIST:
            try:
                # طريقة "السحب السريع" للبيانات الأساسية عشان نتفادى الحظر
                stock = yf.Ticker(ticker)
                
                # جلب السعر الحالي بطريقة خفيفة جداً
                current_price = stock.fast_info['last_price']
                
                # جلب الـ RSI بطلب منفصل وخفيف
                df = stock.history(period='5d', interval='15m', prepost=True)
                
                msg = f"📊 **السهم:** {ticker}\n"
                msg += f"💰 **السعر الحالي:** ${current_price:.2f}\n"
                
                if not df.empty and len(df) > 14:
                    # حساب RSI بسيط وسريع
                    delta = df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    current_rsi = rsi.iloc[-1]
                    msg += f"📉 **RSI:** {current_rsi:.2f}\n"
                
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                time.sleep(5) # ننتظر 5 ثواني بين كل سهم وسهم عشان "نروق" ياهو
                
            except Exception as e:
                print(f"Error skipping {ticker}: {e}")
        
        # ريحه 10 دقائق بعد ما يخلص كل اللستة
        time.sleep(600)

if __name__ == "__main__":
    try:
        Thread(target=scan_markets, daemon=True).start()
        server.run(host='0.0.0.0', port=10000)
    except Exception as e:
        print(e)
