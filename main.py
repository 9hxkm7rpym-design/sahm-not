import telebot
import time
import yfinance as yf
from flask import Flask
from threading import Thread

# بيانات الربط الخاصة بك
TOKEN = "8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo"
CHAT_ID = "1068286006"
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# قائمة المراقبة (Watchlist)
WATCHLIST = ['NVDA', 'TSLA', 'AMZN', 'OXY', 'AAPL', 'MSFT', 'QQQ', '^SPX']

@server.route('/')
def health_check(): 
    return "Falcon Master Radar is Online", 200

def calculate_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def scan_markets():
    bot.send_message(CHAT_ID, "🦅 **تم تشغيل الرادار بنجاح.. جاري فحص الفرص القوية**")
    while True:
        for ticker in WATCHLIST:
            try:
                stock = yf.Ticker(ticker)
                # سحب 5 أيام فقط لضمان السرعة وعدم الحظر
                df = stock.history(period='5d', interval='15m', prepost=True)
                
                if df.empty or len(df) < 15: continue

                # حساب المؤشرات
                rsi_series = calculate_rsi(df)
                current_price = df['Close'].iloc[-1]
                rsi_val = rsi_series.iloc[-1]
                low_2d = df['Low'].min() # أدنى سعر في 5 أيام لوقف الخسارة

                # تحديد قوة الصفقة والأهداف بناءً على RSI
                if rsi_val <= 32:
                    strength = "🔥 قوية جداً (فرصة دخول)"
                    target = current_price * 1.025 # هدف 2.5%
                    strike_offset = 1
                elif rsi_val <= 42:
                    strength = "⚡️ متوسطة (للمراقبة)"
                    target = current_price * 1.015 # هدف 1.5%
                    strike_offset = 2
                elif rsi_val >= 68:
                    strength = "⚠️ تضخم (منطقة خروج)"
                    target = 0
                    strike_offset = 0
                else:
                    strength = "⚪️ ضعيفة (لا توجد إشارة)"
                    target = 0
                    strike_offset = 0

                # تنسيق الرسالة
                msg = f"📊 **السهم: {ticker}**\n"
                msg += f"💰 السعر: ${current_price:.2f}\n"
                msg += f"📈 RSI: {rsi_val:.2f}\n"
                msg += f"💪 القوة: {strength}\n"
                
                if target > 0:
                    msg += f"-------------------\n"
                    msg += f"🎯 الهدف (Target): ${target:.2f}\n"
                    msg += f"🛑 الوقف (Stop): ${low_2d:.2f}\n"
                    msg += f"🎫 سترايك مقترح: {round(current_price + strike_offset)}"
                
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                time.sleep(7) # انتظار 7 ثواني بين الأسهم لتجنب الحظر
            except Exception as e:
                print(f"Error skipping {ticker}: {e}")
                continue
        
        # فحص كل 10 دقائق
        time.sleep(600)

if __name__ == "__main__":
    # تشغيل الرادار في خلفية السيرفر
    Thread(target=scan_markets, daemon=True).start()
    # تشغيل ويب سيرفر عشان Render ما يطفي البوت
    server.run(host='0.0.0.0', port=10000)
