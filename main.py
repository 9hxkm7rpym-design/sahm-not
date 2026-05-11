import telebot
import time
import yfinance as yf
import pandas_ta as ta
from flask import Flask
from threading import Thread

# التوكين الجديد من صورتك الأخيرة والـ ID حقك
TOKEN = "8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

WATCHLIST = ['NVDA', 'TSLA', 'AMZN', 'OXY', 'AAPL', 'MSFT', 'QQQ', '^SPX']

@server.route('/')
def health_check():
    return "Falcon Radar is Online! 🦅", 200

def get_strength(rsi):
    if rsi <= 30 or rsi >= 70: return "🔥 قوية جداً"
    if (rsi <= 40) or (rsi >= 60): return "⚡️ متوسطة"
    return "⚪️ ضعيفة"

def scan_markets():
    while True:
        for ticker in WATCHLIST:
            try:
                df = yf.download(ticker, period='2d', interval='15m', prepost=True, progress=False)
                if df.empty or len(df) < 14: continue
                
                df['RSI'] = ta.rsi(df['Close'], length=14)
                current_price = df['Close'].iloc[-1]
                rsi_value = df['RSI'].iloc[-1]
                
                if str(rsi_value) == 'nan': continue

                strength = get_strength(rsi_value)
                symbol_name = "SPX (سباكس)" if ticker == '^SPX' else ticker
                
                msg = (f"🦅 **رادار الفالكون - تداول ليلي**\n\n"
                       f"📊 السهم: {symbol_name}\n"
                       f"💰 السعر: ${float(current_price):.2f}\n"
                       f"📉 RSI: {float(rsi_value):.2f}\n"
                       f"💪 القوة: {strength}")
                
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                time.sleep(3) 
            except Exception as e:
                print(f"Error: {e}")
        time.sleep(900)

if __name__ == "__main__":
    try:
        # تأكد من إرسال رسالة التفعيل بالتوكين الجديد
        bot.send_message(CHAT_ID, "🌙 **تم تفعيل رادار التداول الليلي بنجاح يا سلطان.**\nجاري فحص السوق الآن...")
        Thread(target=scan_markets, daemon=True).start()
        server.run(host='0.0.0.0', port=10000)
    except Exception as e:
        print(f"Error: {e}")
