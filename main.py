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
report_sent_today = False

class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK - Ultimate Active & Win-Rate Bot Connected!")
        
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
        indicators = data['chart']['result'][0]['indicators']['quote'][0]
        
        current_price = meta['regularMarketPrice']
        previous_close = meta['previousClose']
        change_percent = ((current_price - previous_close) / previous_close) * 100
        
        lows = [l for l in indicators.get('low', []) if l is not None]
        highs = [h for h in indicators.get('high', []) if h is not None]
        
        recent_low = min(lows[-15:]) if lows else current_price * 0.98
        recent_high = max(highs[-15:]) if highs else current_price * 1.02

        price_ranges = [h - l for h, l in zip(highs[-20:], lows[-20:]) if h and l]
        avg_candle_movement = sum(price_ranges) / len(price_ranges) if price_ranges else current_price * 0.005

        return {
            "success": True,
            "price": round(current_price, 2),
            "change": round(change_percent, 2),
            "recent_low": round(recent_low, 2),
            "recent_high": round(recent_high, 2),
            "avg_candle": max(avg_candle_movement, 0.05)
        }
    except Exception as e:
        return {"success": False}

def calculate_real_chart_duration(current_price, target_price, avg_candle):
    distance = abs(target_price - current_price)
    estimated_candles = distance / avg_candle
    
    if estimated_candles <= 15:
        return f"خلال سياق لحظي سريع (متوقع خلال {round(estimated_candles)} دقيقة)"
    elif estimated_candles <= 60:
        hours = round(estimated_candles / 60, 1)
        return f"خلال الجلسة الحالية (متوقع خلال {hours} ساعة)"
    else:
        return "خلال تداولات الجلسة"

def get_ksa_time():
    return datetime.now(timezone(timedelta(hours=3)))

def is_market_open():
    ksa_time = get_ksa_time()
    weekday = ksa_time.weekday()
    if weekday >= 5: 
        return False
        
    current_time = ksa_time.time()
    market_start = dtime(17, 30) 
    market_end = dtime(0, 0)     
    
    if current_time >= market_start or current_time <= market_end:
        return True
    return False

def analyze_market_and_send():
    global signal_counter, daily_stats, report_sent_today, sent_signals
    
    while True:
        ksa_time = get_ksa_time()
        
        if ksa_time.hour == 9 and ksa_time.minute == 0:
            if report_sent_today:
                daily_stats = {"wins": 0, "losses": 0}
                sent_signals.clear()
                report_sent_today = False

        if not is_market_open():
            time.sleep(60)
            continue

        # 1. تتبع دقيق للأهداف ووقف الخسارة الفني لايف
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
                        send_telegram_message(f"🎯 *هدف محقق باحترافية! (+)*\n• السهم: `{ticker}` | CALL\n• السعر الحالي: `${current_price}` ✅")
                        tickers_to_remove.append(ticker)
                    elif current_price <= stop_loss:
                        daily_stats["losses"] += 1
                        send_telegram_message(f"🛑 *وقف خسارة فني (-)*\n• السهم: `{ticker}` | CALL\n• السعر الحالي: `${current_price}` ❌")
                        tickers_to_remove.append(ticker)
                elif trade_type == "PUT":
                    if current_price <= target1:
                        daily_stats["wins"] += 1
                        send_telegram_message(f"🎯 *هدف محقق باحترافية! (+)*\n• السهم: `{ticker}` | PUT\n• السعر الحالي: `${current_price}` ✅")
                        tickers_to_remove.append(ticker)
                    elif current_price >= stop_loss:
                        daily_stats["losses"] += 1
                        send_telegram_message(f"🛑 *وقف خسارة فني (-)*\n• السهم: `{ticker}` | PUT\n• السعر الحالي: `${current_price}` ❌")
                        tickers_to_remove.append(ticker)
                        
        for t in tickers_to_remove:
            del active_trades[t]

        # 2. فحص نشط جداً (0.8%) لتدفق الصفقات مع أمان الوقف الفني
        for ticker in WATCHLIST:
            if ticker in active_trades or ticker in sent_signals:
                continue
                
            market = get_real_market_data(ticker)
            if market.get("success"):
                change_val = market["change"]
                current_price = market["price"]
                recent_low = market["recent_low"]
                recent_high = market["recent_high"]
                avg_candle = market["avg_candle"]
                
                if change_val >= 0.8:
                    signal_counter += 1
                    grade = "🔥 صفقة نخبة (درجة A+)" if change_val >= 2.0 else "⭐ صفقة نشطة (درجة A)"
                    
                    entry_min = round(current_price * 0.998, 2)
                    entry_max = round(current_price * 1.002, 2)
                    target1 = round(current_price * 1.012, 2)
                    target2 = round(current_price * 1.020, 2)
                    stop_loss = round(min(recent_low, current_price * 0.985), 2)
                    
                    dynamic_duration = calculate_real_chart_duration(current_price, target1, avg_candle)
                    
                    active_trades[ticker] = {
                        "id": signal_counter, "type": "CALL", "entry": current_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    
                    msg = (
                        f"🚀 *فرصة أوبشن نشطة #{signal_counter}*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 *السهم:* `{ticker}` | `CALL (صعود) 🟢`\n"
                        f"💵 *السعر الحالي:* `${current_price}` (+{change_val}%)\n"
                        f"🏆 *التقييم:* `{grade}`\n"
                        f"🎯 *الدخول:* `${entry_min}` ⟵ `${entry_max}`\n"
                        f"🎯 *الأهداف:* `${target1}` | `${target2}`\n"
                        f"🛑 *الوقف الذكي الفني:* `${stop_loss}`\n"
                        f"⏳ *المدى الزمني:* `{dynamic_duration}`"
                    )
                    send_telegram_message(msg)
                    time.sleep(1)
                    
                elif change_val <= -0.8:
                    signal_counter += 1
                    grade = "🔥 صفقة نخبة (درجة A+)" if change_val <= -2.0 else "⭐ صفقة نشطة (درجة A)"
                    
                    entry_min = round(current_price * 0.998, 2)
                    entry_max = round(current_price * 1.002, 2)
                    target1 = round(current_price * 0.988, 2)
                    target2 = round(current_price * 0.980, 2)
                    stop_loss = round(max(recent_high, current_price * 1.015), 2)
                    
                    dynamic_duration = calculate_real_chart_duration(current_price, target1, avg_candle)
                    
                    active_trades[ticker] = {
                        "id": signal_counter, "type": "PUT", "entry": current_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    
                    msg = (
                        f"🚀 *فرصة أوبشن نشطة #{signal_counter}*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 *السهم:* `{ticker}` | `PUT (هبوط) 🔴`\n"
                        f"💵 *السعر الحالي:* `${current_price}` ({change_val}%)\n"
                        f"🏆 *التقييم:* `{grade}`\n"
                        f"🎯 *الدخول:* `${entry_min}` ⟵ `${entry_max}`\n"
                        f"🎯 *الأهداف:* `${target1}` | `${target2}`\n"
                        f"🛑 *الوقف الذكي الفني:* `${stop_loss}`\n"
                        f"⏳ *المدى الزمني:* `{dynamic_duration}`"
                    )
                    send_telegram_message(msg)
                    time.sleep(1)

        time.sleep(30)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    try:
        send_telegram_message("⚡ *تم تشغيل النسخة النشطة المتوازنة: صفقات سريعة متدفقة + وقف فني ذكي يحمي رأس المال!*")
    except:
        pass
        
    analyze_market_and_send()
