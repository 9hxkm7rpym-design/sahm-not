import os
import time
import requests
from datetime import datetime, time as dtime, timedelta, timezone
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
daily_stats = {"wins": 0, "losses": 0}

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
        
        return {
            "success": True,
            "price": round(current_price, 2),
            "change": round(change_percent, 2)
        }
    except Exception as e:
        return {"success": False}

def is_market_open():
    """ التحقق بدقة من توقيت السعودية (UTC+3) وساعات السوق الأمريكي الشتوية (5:30 عصراً - 12:00 ليلاً) ومن الإثنين للجمعة """
    # ضبط الوقت بتوقيت المملكة العربية السعودية (UTC+3) بشكل دقيق وثابت
    ksa_time = datetime.now(timezone(timedelta(hours=3)))
    weekday = ksa_time.weekday() # 0 = الإثنين إلى 4 = الجمعة
    
    if weekday >= 5: # السبت والأحد إجازة
        return False
        
    current_time = ksa_time.time()
    market_start = dtime(17, 30) # 5:30 عصراً
    market_end = dtime(0, 0)     # 12:00 ليلاً
    
    # السوق مفتوح بين 5:30 عصراً و 12:00 ليلاً
    if current_time >= market_start or current_time <= market_end:
        return True
    return False

def analyze_market_and_send():
    global signal_counter, daily_stats
    
    while True:
        # فحص هل السوق مفتوح أم لا بتوقيت السعودية الصحيح
        if not is_market_open():
            time.sleep(60)
            continue

        # 1. متابعة الأهداف ووقف الخسارة بدقة لحظية للصفقات المفتوحة
        tickers_to_remove = []
        for ticker, trade in active_trades.items():
            market = get_real_market_data(ticker)
            if market.get("success"):
                current_price = market["price"]
                trade_type = trade["type"]
                target1 = trade["target1"]
                stop_loss = trade["stop_loss"]
                
                if trade_type == "CALL":
                    if current_price >= target1:
                        daily_stats["wins"] += 1
                        send_telegram_message(f"🎯 *هدف محقق بنجاح! (+)*\n• السهم: `{ticker}` | CALL\n• السعر الحالي: `${current_price}`\n• الحالة: تم تحقيق الهدف الأول ✅")
                        tickers_to_remove.append(ticker)
                    elif current_price <= stop_loss:
                        daily_stats["losses"] += 1
                        send_telegram_message(f"🛑 *وقف خسارة (-)*\n• السهم: `{ticker}` | CALL\n• السعر الحالي: `${current_price}`\n• الحالة: تم ضرب وقف الخسارة لحماية رأس المال ❌")
                        tickers_to_remove.append(ticker)
                elif trade_type == "PUT":
                    if current_price <= target1:
                        daily_stats["wins"] += 1
                        send_telegram_message(f"🎯 *هدف محقق بنجاح! (+)*\n• السهم: `{ticker}` | PUT\n• السعر الحالي: `${current_price}`\n• الحالة: تم تحقيق الهدف الأول ✅")
                        tickers_to_remove.append(ticker)
                    elif current_price >= stop_loss:
                        daily_stats["losses"] += 1
                        send_telegram_message(f"🛑 *وقف خسارة (-)*\n• السهم: `{ticker}` | PUT\n• السعر الحالي: `${current_price}`\n• الحالة: تم ضرب وقف الخسارة لحماية رأس المال ❌")
                        tickers_to_remove.append(ticker)
                        
        for t in tickers_to_remove:
            del active_trades[t]

        # 2. فحص اتجاه السوق العام (SPY) بمرونة ذكية
        spy_market = get_real_market_data("SPY")
        market_trend = "NEUTRAL"
        if spy_market.get("success"):
            if spy_market["change"] > 0.2:
                market_trend = "BULLISH"
            elif spy_market["change"] < -0.2:
                market_trend = "BEARISH"

        # 3. اصطياد الفرص أثناء ساعات العمل الرسمية فقط
        for ticker in WATCHLIST:
            if ticker in active_trades or ticker in sent_signals or ticker == "SPY":
                continue
                
            market = get_real_market_data(ticker)
            if market.get("success"):
                change_val = market["change"]
                current_price = market["price"]
                
                if abs(change_val) >= 1.8:
                    
                    # التصنيف بالعربي بالكامل وبدون إنجليزية ملخبطة
                    if abs(change_val) >= 2.5:
                        grade = "🔥 النخبة (درجة A+) - عزم مؤسساتي خارق"
                        duration = "سكالبينج سريع ومضمون (5 إلى 15 دقيقة)"
                        is_elite = True  
                    else:
                        grade = "⭐ ممتاز (درجة A) - زخم قوي مؤكد"
                        duration = "تداول لحظي (15 إلى 30 دقيقة)"
                        is_elite = False

                    # فلترة صفقات "ممتاز" مع اتجاه السوق العام
                    if not is_elite:
                        if change_val > 0 and market_trend == "BEARISH":
                            continue
                        if change_val < 0 and market_trend == "BULLISH":
                            continue

                    if change_val > 0:
                        signal_counter += 1
                        entry_min = round(current_price * 0.998, 2)
                        entry_max = round(current_price * 1.002, 2)
                        target1 = round(current_price * 1.015, 2)
                        target2 = round(current_price * 1.025, 2)
                        stop_loss = round(current_price * 0.988, 2)
                        
                        active_trades[ticker] = {
                            "id": signal_counter, "type": "CALL", "entry": current_price,
                            "target1": target1, "stop_loss": stop_loss
                        }
                        sent_signals.add(ticker)
                        
                        msg = (
                            f"🔥 *فرصة عالية الدقة #{signal_counter}*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"📌 *السهم:* `{ticker}`\n"
                            f"📈 *النوع:* `CALL (صعود) 🟢`\n"
                            f"💵 *السعر الحالي:* `${current_price}` (+{change_val}%)\n"
                            f"🏆 *التقييم:* `{grade}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"🎯 *منطقة الدخول:* `${entry_min}` ⟵ `${entry_max}`\n"
                            f"🎯 *الأهداف:* `${target1}` | `${target2}`\n"
                            f"🛑 *وقف الخسارة:* `${stop_loss}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⏳ *المدة المقترحة:* `{duration}`\n"
                            f"⚠️ *تنبيه هام:* إغلاق إجباري قبل نهاية الجلسة الشتوية!"
                        )
                        send_telegram_message(msg)
                        time.sleep(1)
                        
                    elif change_val < 0:
                        signal_counter += 1
                        entry_min = round(current_price * 0.998, 2)
                        entry_max = round(current_price * 1.002, 2)
                        target1 = round(current_price * 0.985, 2)
                        target2 = round(current_price * 0.975, 2)
                        stop_loss = round(current_price * 1.012, 2)
                        
                        active_trades[ticker] = {
                            "id": signal_counter, "type": "PUT", "entry": current_price,
                            "target1": target1, "stop_loss": stop_loss
                        }
                        sent_signals.add(ticker)
                        
                        msg = (
                            f"🔥 *فرصة عالية الدقة #{signal_counter}*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"📌 *السهم:* `{ticker}`\n"
                            f"📉 *النوع:* `PUT (هبوط) 🔴`\n"
                            f"💵 *السعر الحالي:* `${current_price}` ({change_val}%)\n"
                            f"🏆 *التقييم:* `{grade}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"🎯 *منطقة الدخول:* `${entry_min}` ⟵ `${entry_max}`\n"
                            f"🎯 *الأهداف:* `${target1}` | `${target2}`\n"
                            f"🛑 *وقف الخسارة:* `${stop_loss}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⏳ *المدة المقترحة:* `{duration}`\n"
                            f"⚠️ *تنبيه هام:* إغلاق إجباري قبل نهاية الجلسة الشتوية!"
                        )
                        send_telegram_message(msg)
                        time.sleep(1)

        time.sleep(30)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    try:
        send_telegram_message("⚡ *تم ضبط توقيت السعودية (UTC+3) بدقة تامة؛ البوت الآن مربوط حصرياً بساعات تداول السوق الأمريكي الرسمية ولن يرسل شيئاً خارجها!*")
    except:
        pass
        
    analyze_market_and_send()
