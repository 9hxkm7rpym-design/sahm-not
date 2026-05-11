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

# قائمة المراقبة (تم إضافة Microsoft و AMD)
WATCHLIST = ['NVDA', 'TSLA', 'AMZN', 'OXY', 'AAPL', 'MSFT', 'AMD', 'QQQ', '^SPX']

@server.route('/')
def health_check(): return "Falcon Ultimate Stable Online", 200

def calculate_indicators(df):
    # حساب RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # حساب المتوسط المتحرك SMA 20
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # حساب متوسط الحجم
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    return df

def scan_markets():
    bot.send_message(CHAT_ID, "🦅 **رادار النخبة يعمل الآن.. تحليل شامل (RSI + SMA + Volume) جاهز يا سلطان!**")
    while True:
        for ticker in WATCHLIST:
            try:
                stock = yf.Ticker(ticker)
                # سحب بيانات Pre-market لضمان العمل وقت إغلاق السوق
                df = stock.history(period='5d', interval='15m', prepost=True)
                if df.empty or len(df) < 20: continue

                df = calculate_indicators(df)
                current_price = df['Close'].iloc[-1]
                rsi_val = df['RSI'].iloc[-1]
                sma_val = df['SMA_20'].iloc[-1]
                current_vol = df['Volume'].iloc[-1]
                avg_vol = df['Vol_Avg'].iloc[-1]
                
                # حساب الدعم والمقاومة
                support = df['Low'].tail(40).min()
                resistance = df['High'].tail(40).max()

                # تحديد الاتجاه والدرجة
                is_call = rsi_val <= 50
                direction = "🟢 كول (CALL)" if is_call else "🔴 بوت (PUT)"
                
                # معايير الثقة (فحص الحجم والـ RSI)
                vol_status = "عالية ✅" if current_vol > avg_vol else "ضعيفة ⚠️"
                confidence = "عالية جداً 🔥" if (rsi_val <= 35 or rsi_val >= 65) and current_vol > avg_vol else "متوسطة ⚡️"

                # حساب الأهداف الثلاثة
                if is_call:
                    t1, t2, t3 = current_price * 1.01, current_price * 1.025, resistance
                    stop, strike = support, int(current_price) + 1
                else:
                    t1, t2, t3 = current_price * 0.99, current_price * 0.975, support
                    stop, strike = resistance, int(current_price) - 1

                report = (
                    f"🤖 **رسالة من البوت الآلي** 🤖\n"
                    f"📊 **إشارة تداول {ticker}**\n"
                    f"💰 **السعر الحالي: ${current_price:.2f}**\n"
                    f"📈 **RSI:** {int(rsi_val)} | **SMA:** {int(sma_val)}\n"
                    f"📊 **السيولة:** {vol_status}\n"
                    f"-------------------\n"
                    f"**الاتجاه: {direction}**\n"
                    f"🟡 **درجة الثقة:** {confidence}\n"
                    f"🕒 **الصلاحية:** Intraday / Weekly\n\n"
                    f"⚙️ **خطة التنفيذ:**\n"
                    f"🔹 **منطقة الدخول:** {int(current_price)}\n"
                    f"🔹 **مستوى الوقف:** {int(stop)}\n"
                    f"🎯 **هدف 1:** {int(t1)}\n"
                    f"🎯 **هدف 2:** {int(t2)}\n"
                    f"🎯 **هدف 3:** {int(t3)}\n\n"
                    f"📋 **العقد المقترح:**\n"
                    f"{direction} | Strike: {strike}"
                )
                
                bot.send_message(CHAT_ID, report, parse_mode="Markdown")
                time.sleep(12) # تأخير بسيط لتجنب الحظر من التليجرام
            except Exception as e:
                print(f"Error scanning {ticker}: {e}")
                continue
        time.sleep(600) # فحص كل 10 دقائق

if __name__ == "__main__":
    # تشغيل السيرفر والبوت في خيوط منفصلة لضمان الاستقرار
    Thread(target=scan_markets, daemon=True).start()
    server.run(host='0.0.0.0', port=10000)
