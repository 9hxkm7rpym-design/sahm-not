import os
import time
import requests
import yfinance as yf
from datetime import datetime
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==================== إعدادات تليجرام ====================
TELEGRAM_BOT_TOKEN = "8472180858:AAG2eMBTuzRMz-tLkT2MV9ow_YjeUbXAbyY"
TELEGRAM_CHAT_ID = "1068286006"

# ==================== سيرفر ويب لتجنب مشاكل رندر ====================
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Radar Club Pro Bot is Active & Running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.json()
    except Exception as e:
        print(f"خطأ في إرسال رسالة تليجرام: {e}")

# ==================== قائمة الأسهم المراقبة (Watchlist) ====================
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC",
    "PLTR", "BA", "DIS", "PYPL", "SQ", "COIN", "MARA", "RIVN", "NIO", "SNAP",
    "UBER", "ROKU", "SHOP", "BABA", "XOM", "JPM", "BAC", "PFE", "SPY"
]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def check_market_momentum():
    print("🚀 جاري فحص السوق بأدق معايير التحليل الفني (RSI + الفوليوم العالي)...")
    
    for symbol in WATCHLIST:
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            stock = yf.Ticker(symbol, session=session)
            df = stock.history(period="5d", interval="1h")
            
            if df.empty or len(df) < 20:
                continue
                
            current_price = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            price_change = ((current_price - prev_close) / prev_close) * 100
            
            current_volume = float(df['Volume'].iloc[-1])
            avg_volume = float(df['Volume'].mean())
            
            # حساب مؤشر القوة النسبية RSI لدقة أعلى
            rsi_value = calculate_rsi(df['Close'])
            
            # فلترة ذكية لصفقات الـ CALL (عزم صعودي مؤكد بنسبة نجاح عالية)
            if price_change >= 1.2 and current_volume > (avg_volume * 1.2) and 45 <= rsi_value <= 70:
                
                entry_low = round(current_price * 0.998, 2)
                entry_high = round(current_price * 1.002, 2)
                target_1 = round(current_price * 1.025, 2)
                target_2 = round(current_price * 1.05, 2)
                stop_loss = round(current_price * 0.982, 2)
                
                message = (
                    f"🔥 *صفقة أوبشن (CALL) عالية النقاء* 🟢\n\n"
                    f"📌 *الرمز:* `{symbol}`\n"
                    f"💵 *السعر الحالي:* `${current_price:.2f}`\n"
                    f"📊 *مؤشر RSI:* `{rsi_value:.1f}` *(زخم صاعد صحي)*\n\n"
                    f"🎯 *منطقة الدخول الذكية:* \n`${entry_low} - ${entry_high}`\n\n"
                    f"📈 *الأهداف المرصودة:*\n"
                    f"• *الهدف الأول:* `${target_1}` 🟢\n"
                    f"• *الهدف الثاني:* `${target_2}` 🚀\n"
                    f"🛑 *وقف الخسارة الآمن:* `${stop_loss}`\n\n"
                    f"⚡ *نسبة التغير وفوليوم السيولة:* `+{price_change:.2f}%`"
                )
                
                send_telegram_message(message)
                print(f"تم إرسال صفقة CALL قوية للسهم: {symbol}")

            # فلترة ذكية لصفقات الـ PUT (انهيار وتأكيد بيعي قوي)
            elif price_change <= -1.2 and current_volume > (avg_volume * 1.2) and 30 <= rsi_value <= 55:
                
                entry_low = round(current_price * 0.998, 2)
                entry_high = round(current_price * 1.002, 2)
                target_1 = round(current_price * 0.975, 2)
                target_2 = round(current_price * 0.95, 2)
                stop_loss = round(current_price * 1.018, 2)
                
                message = (
                    f"🩸 *صفقة أوبشن (PUT) عالية النقاء* 🔴\n\n"
                    f"📌 *الرمز:* `{symbol}`\n"
                    f"💵 *السعر الحالي:* `${current_price:.2f}`\n"
                    f"📊 *مؤشر RSI:* `{rsi_value:.1f}` *(ضغط بيعي وهبوط)*\n\n"
                    f"🎯 *منطقة الدخول الذكية:* \n`${entry_low} - ${entry_high}`\n\n"
                    f"📉 *الأهداف الهبوطية المرصودة:*\n"
                    f"• *الهدف الأول:* `${target_1}` 🔴\n"
                    f"• *الهدف الثاني:* `${target_2}` 🎯\n"
                    f"🛑 *وقف الخسارة الآمن:* `${stop_loss}`\n\n"
                    f"⚡ *نسبة التغير وفوليوم السيولة:* `{price_change:.2f}%`"
                )
                
                send_telegram_message(message)
                print(f"تم إرسال صفقة PUT قوية للسهم: {symbol}")
                
            time.sleep(1)
        except Exception as e:
            print(f"خطأ أثناء معالجة السهم {symbol}: {e}")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    print("🤖 رادار صفقات الأوبشن الاحترافي يعمل الآن...")
    while True:
        check_market_momentum()
        time.sleep(300)
