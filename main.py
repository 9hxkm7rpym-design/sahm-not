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

# القائمة المحدثة (AMD, MSFT, NVDA, TSLA, AMZN, OXY, AAPL, QQQ, SPX)
WATCHLIST = ['NVDA', 'TSLA', 'AMZN', 'OXY', 'AAPL', 'MSFT', 'AMD', 'QQQ', '^SPX']

@server.route('/')
def health_check(): return "Falcon Expert Pro Online", 200

def calculate_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def scan_markets():
    bot.send_message(CHAT_ID, "🦅 **تم تحديث المحلل الذكي: الآن يدعم تحديد (كول/بوت) وأرقام صحيحة**")
    while True:
        for ticker in WATCHLIST:
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period='5d', interval='15m', prepost=True)
                if df.empty or len(df) < 15: continue

                rsi_series = calculate_rsi(df)
                current_price = df['Close'].iloc[-1]
                rsi_val = rsi_series.iloc[-1]
                
                # حساب الدعم والمقاومة اللحظية
                support = df['Low'].tail(40).min()
                resistance = df['High'].tail(40).max()

                # تحليل نوع العقد والقوة
                contract_type = "غير محدد"
                strength = "⚪️ ضعيفة (انتظر إشارة أفضل)"
                target = 0
                stop = 0
                strike = 0

                if rsi_val <= 32:
                    strength = "🔥 قوية جداً (فرصة انفجار للأعلى)"
                    contract_type = "🟢 كول (CALL)"
                    target = resistance
                    stop = support
                    strike = int(current_price) + 1
                elif rsi_val >= 68:
                    strength = "⚠️ تضخم عالي (توقع تصحيح للأسفل)"
                    contract_type = "🔴 بوت (PUT)"
                    target = support
                    stop = resistance
                    strike = int(current_price) - 1
                elif 32 < rsi_val <= 42:
                    strength = "⚡️ متوسطة (تجميع إيجابي)"
                    contract_type = "🟢 كول (CALL)"
                    target = current_price * 1.02
                    stop = support
                    strike = int(current_price) + 2
                elif 58 <= rsi_val < 68:
                    strength = "📉 متوسطة (تراجع تدريجي)"
                    contract_type = "🔴 بوت (PUT)"
                    target = current_price * 0.98
                    stop = resistance
                    strike = int(current_price) - 2

                # بناء رسالة التحليل
                msg = f"📊 **تحليل السهم: {ticker}**\n"
                msg += f"💰 السعر: ${current_price:.2f} | RSI: {rsi_val:.2f}\n"
                msg += f"💪 الحالة: {strength}\n"
                msg += f"-------------------\n"
                
                if target > 0:
                    msg += f"🎫 نوع العقد: **{contract_type}**\n"
                    msg += f"💎 السترايك: {int(strike)}\n"
                    msg += f"🎯 الهدف: ${int(target)}\n"
                    msg += f"🛑 الوقف: ${int(stop)}"
                else:
                    msg += f"ℹ️ نصيحة: السهم في مسار عرضي، لا ينصح بالدخول الآن."

                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                time.sleep(8) 
            except: continue
        time.sleep(600)

if __name__ == "__main__":
    Thread(target=scan_markets, daemon=True).start()
    server.run(host='0.0.0.0', port=10000)
