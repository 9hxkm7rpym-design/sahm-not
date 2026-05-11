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

# قائمة المراقبة المختارة بعناية
WATCHLIST = ['NVDA', 'TSLA', 'AMZN', 'OXY', 'AAPL', 'MSFT', 'AMD', 'QQQ', '^SPX']

@server.route('/')
def health_check(): return "Falcon Hybrid-Trader Online", 200

def calculate_rsi(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def scan_markets():
    bot.send_message(CHAT_ID, "🦅 **تم تحديث الرادار (Intraday/Weekly).. جاري القنص يا سلطان!**")
    while True:
        for ticker in WATCHLIST:
            try:
                stock = yf.Ticker(ticker)
                # سحب بيانات تغطي المضاربة اليومية والأسبوعية
                df = stock.history(period='5d', interval='15m', prepost=True)
                if df.empty or len(df) < 15: continue

                rsi_val = calculate_rsi(df).iloc[-1]
                current_price = df['Close'].iloc[-1]
                support = df['Low'].tail(50).min()
                resistance = df['High'].tail(50).max()

                # إرسال التقرير فقط عند وجود إشارة واضحة (قوية أو متوسطة)
                if rsi_val <= 42 or rsi_val >= 58:
                    is_call = rsi_val <= 50
                    direction = "🟢 كول (CALL)" if is_call else "🔴 بوت (PUT)"
                    confidence = "عالية 🔥" if (rsi_val <= 32 or rsi_val >= 68) else "متوسطة ⚡️"
                    
                    # حساب الأهداف الثلاثة (من اللحظي إلى الأسبوعي)
                    if is_call:
                        t1 = current_price * 1.01  # هدف لحظي (Intraday)
                        t2 = current_price * 1.03  # هدف يومي
                        t3 = resistance            # هدف أسبوعي (المقاومة)
                        stop = support
                        strike = int(current_price) + 1
                    else:
                        t1 = current_price * 0.99  # هدف لحظي
                        t2 = current_price * 0.97  # هدف يومي
                        t3 = support               # هدف أسبوعي (الدعم)
                        stop = resistance
                        strike = int(current_price) - 1

                    report = (
                        f"🤖 **رسالة من البوت الآلي** 🤖\n"
                        f"📊 **إشارة تداول {ticker}**\n"
                        f"⛔️ **تحذير** ⛔️\n"
                        f"إشارة التداول تحت التجربة والمراقبة\n\n"
                        f"**الاتجاه: {direction}**\n\n"
                        f"🟡 **درجة الثقة:** {confidence}\n"
                        f"🕒 **صلاحية العقد:** Intraday / Weekly\n\n"
                        f"⚙️ **خطة التنفيذ:**\n"
                        f"🔹 **نوع الدخول:** اختراق لحظي\n"
                        f"🔹 **منطقة الدخول:** {int(current_price)}\n"
                        f"🔹 **مستوى الوقف:** {int(stop)}\n"
                        f"🎯 **الهدف 1:** {int(t1)}\n"
                        f"🎯 **الهدف 2:** {int(t2)}\n"
                        f"🎯 **الهدف 3:** {int(t3)}\n\n"
                        f"📋 **العقد المقترح:**\n"
                        f"{direction} | Strike: {strike}"
                    )
                    bot.send_message(CHAT_ID, report, parse_mode="Markdown")
                
                time.sleep(10) # انتظار بين الأسهم
            except: continue
        time.sleep(600) # فحص كل 10 دقائق

if __name__ == "__main__":
    Thread(target=scan_markets, daemon=True).start()
    server.run(host='0.0.0.0', port=10000)
