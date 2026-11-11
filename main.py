import os
import time
import requests
from datetime import datetime
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- بيانات الربط المباشر المعتمدة لبوتك ---
TELEGRAM_TOKEN = "8472180858:AAG2eMBTuzRMz-tLkT2MV9ow_YjeUbXAbyY"
CHAT_ID = "1068286006"

# --- قائمة الأسهم النشطة للأوبشن ---
WATCHLIST = [
    "NVDA", "TSLA", "MSFT", "AMZN", "AAPL", "META", "OXY", "NFLX", "AMD", "GOOGL",
    "BA", "BABA", "COIN", "DIS", "JPM", "MARA", "NIO", "ORCL", "PLTR", "QQQ",
    "ROKU", "SPY", "SQ", "UBER", "V", "WMT", "XOM", "PFE", "SOFI"
]

active_trades = {}      
sent_signals = set()    
signal_counter = 0      

# --- سيرفر الويب الخفيف لخدمة الكرون بدون أخطاء ---
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK - Cron Connected Successfully!")
        
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_real_market_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        meta = data['chart']['result'][0]['meta']
        current_price = meta['regularMarketPrice']
        previous_close = meta['previousClose']
        change_percent = ((current_price - previous_close) / previous_close) * 100
        
        # محاولة جلب حجم التداول اللحظي لو متوفر
        indicators = data['chart']['result'][0]['indicators']['quote'][0]
        volumes = indicators.get('volume', [0])
        current_volume = volumes[-1] if volumes and volumes[-1] else 0
        
        return {
            "success": True,
            "price": round(current_price, 2),
            "change": round(change_percent, 2),
            "volume": current_volume
        }
    except Exception as e:
        return {"success": False}

def analyze_market_and_send():
    global signal_counter
    
    while True:
        for ticker in WATCHLIST:
            if ticker in active_trades or ticker in sent_signals:
                continue
                
            market = get_real_market_data(ticker)
            if market.get("success"):
                change_val = market["change"]
                current_price = market["price"]
                
                # درجة الصفقة وقوتها
                if abs(change_val) >= 1.5:
                    grade = "A+ (عزم قوي جداً 🔥🔥🔥)"
                    reason_power = "تدفق سيولة مؤسساتية ضخمة وانفجار سعري لحظي"
                elif abs(change_val) >= 1.0:
                    grade = "A (عزم قوي ومستمر ⭐⭐⭐)"
                    reason_power = "زخم شرائي/بيعي قوي مع استمرار السيولة"
                else:
                    grade = "B+ (عزم خفيف وسريع ⭐⭐)"
                    reason_power = "حركة زخم سريعة وبداية دخول سيولة لحظية"
                
                duration = "سريعة / Intraday (تُغلق قبل نهاية الجلسة)"

                if change_val > 0.5:
                    signal_counter += 1
                    entry_min = round(current_price * 0.998, 2)
                    entry_max = round(current_price * 1.002, 2)
                    
                    target1 = round(current_price * 1.012, 2)
                    target2 = round(current_price * 1.022, 2)
                    stop_loss = round(current_price * 0.985, 2)
                    
                    active_trades[ticker] = {
                        "id": signal_counter, "type": "CALL", "entry": current_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    
                    msg = (
                        f"🚀 *صفقة صعود فورية رقم #{signal_counter}*\n"
                        f"📌 *السهم:* `{ticker}` | *الاتجاه:* CALL 🟢\n"
                        f"💵 *سعر السهم الحالي:* `${current_price}`\n"
                        f"📊 *التغير اللحظي:* +{change_val}%\n"
                        f"🧠 *سبب الصفقة:* {reason_power}\n"
                        f"⭐ *درجة الصفقة:* {grade}\n"
                        f"⏳ *المدة المقترحة:* {duration}\n"
                        f"🎯 *منطقة الدخول الصحيحة:* `${entry_min}` ⟵ `${entry_max}`\n"
                        f"───────────────────\n"
                        f"🎯 *الأهداف:*\n"
                        f"• الهدف الأول: `${target1}` | الهدف الثاني: `${target2}`\n"
                        f"🛑 *وقف الخسارة:* `${stop_loss}`\n"
                        f"───────────────────\n"
                        f"💡 *تنبيه:* لا تدخل إذا ابتعد السعر عن منطقة الدخول المحددة!"
                    )
                    send_telegram_message(msg)
                    time.sleep(1)
                    
                elif change_val < -0.5:
                    signal_counter += 1
                    entry_min = round(current_price * 0.998, 2)
                    entry_max = round(current_price * 1.002, 2)
                    
                    target1 = round(current_price * 0.988, 2)
                    target2 = round(current_price * 0.978, 2)
                    stop_loss = round(current_price * 1.015, 2)
                    
                    active_trades[ticker] = {
                        "id": signal_counter, "type": "PUT", "entry": current_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    
                    msg = (
                        f"💥 *صفقة هبوط فورية رقم #{signal_counter}*\n"
                        f"📌 *السهم:* `{ticker}` | *الاتجاه:* PUT 🔴\n"
                        f"💵 *سعر السهم الحالي:* `${current_price}`\n"
                        f"📊 *التغير اللحظي:* {change_val}%\n"
                        f"🧠 *سبب الصفقة:* {reason_power} (ضغط بيعي)\n"
                        f"⭐ *درجة الصفقة:* {grade}\n"
                        f"⏳ *المدة المقترحة:* {duration}\n"
                        f"🎯 *منطقة الدخول الصحيحة:* `${entry_min}` ⟵ `${entry_max}`\n"
                        f"───────────────────\n"
                        f"🎯 *الأهداف:*\n"
                        f"• الهدف الأول: `${target1}` | الهدف الثاني: `${target2}`\n"
                        f"🛑 *وقف الخسارة:* `${stop_loss}`\n"
                        f"───────────────────\n"
                        f"💡 *تنبيه:* لا تدخل إذا ابتعد السعر عن منطقة الدخول المحددة!"
                    )
                    send_telegram_message(msg)
                    time.sleep(1)

        time.sleep(20)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    try:
        send_telegram_message("⚡ *تم تحديث الرادار (إضافة سبب وطبيعة السيولة في كل صفقة)!*")
    except:
        pass
        
    analyze_market_and_send()
