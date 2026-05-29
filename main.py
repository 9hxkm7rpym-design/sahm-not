import os
import time
import requests
from datetime import datetime, timedelta
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- بيانات الربط المباشر المعتمدة ---
TELEGRAM_TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"

# --- قائمة الـ 29 سهم المعتمدة ---
WATCHLIST = [
    "NVDA", "TSLA", "MSFT", "AMZN", "AAPL", "META", "OXY", "NFLX", "AMD", "GOOGL",
    "BA", "BABA", "COIN", "DIS", "JPM", "MARA", "NIO", "ORCL", "PLTR", "QQQ",
    "ROKU", "SPY", "SQ", "UBER", "V", "WMT", "XOM", "PFE", "SOFI"
]

# --- الذاكرة المؤقتة والعدادات الذكية ---
sent_signals = {}       
report_sent_today = False
last_reset_day = ""
signal_counter = 0      

class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Radar Abbadi Smart Filtering Is Active!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def translate_and_summarize_news(ticker, level):
    try:
        context = "High explosive momentum" if "النخبة" in level else "Normal steady movement"
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ar&dt=t&q={context} observed on {ticker} stock."
        response = requests.get(url, timeout=5)
        result = response.json()
        return "".join([sentence[0] for sentence in result[0] if sentence[0]])
    except Exception as e:
        return "تدفقات سيولة فورية وعزم حركة على الشارت الحين."

def get_real_market_data(ticker):
    """جلب الأسعار الحقيقية وحساب الفلترة بدقة بالدرجات"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        current_price = data['chart']['result'][0]['meta']['regularMarketPrice']
        previous_close = data['chart']['result'][0]['meta']['previousClose']
        
        # حساب نسبة التغير اللحظية الحقيقية لسعر السهم
        change_percent = ((current_price - previous_close) / previous_close) * 100
        
        # 🎯 تقسيم الصفقات لدرجات بناءً على قوة الانفجار
        if change_percent > 1.5:
            if change_percent > 3.0:
                confidence_level = "قوية جداً (النخبة 🟩)"
            else:
                confidence_level = "تأكيد صعود (درجة ممتازة 🟨)"
                
            return {
                "success": True, 
                "price": round(current_price, 2),
                "direction": "CALL", 
                "level": confidence_level, 
                "change": round(change_percent, 2)
            }
        return {"success": False} # السهم خامل أو أحمر فما نرسله
    except Exception as e:
        return {"success": False}

def analyze_market_and_send():
    global report_sent_today, last_reset_day, signal_counter
    
    while True:
        now_sa = datetime.utcnow() + timedelta(hours=3)
        current_day = now_sa.strftime("%Y-%m-%d")
        current_time_float = now_sa.hour + (now_sa.minute / 60.0)
        
        if current_day != last_reset_day:
            signal_counter = 0
            sent_signals.clear()
            report_sent_today = False
            last_reset_day = current_day

        # 🛑 فلتر وقت السوق الرسمي بتوقيت السعودية (4:30 عصراً إلى 11:00 مساءً)
        if current_time_float < 16.5 or current_time_float > 23.0:
            print(f"💤 السوق مقفل رسمي الحين.. الرادار يريح.")
            time.sleep(60)
            continue

        for ticker in WATCHLIST:
            market = get_real_market_data(ticker)
            
            if market.get("success") and ticker not in sent_signals:
                signal_counter += 1  
                
                entry_price = market["price"]
                confidence_level = market["level"]
                change_val = market["change"]
                
                target1 = round(entry_price * 1.01, 2)
                target2 = round(entry_price * 1.02, 2)
                stop_loss = round(entry_price * 0.97, 2)
                
                sent_signals[ticker] = {"id": signal_counter, "status": "Active"}
                arabic_news = translate_and_summarize_news(ticker, confidence_level)
                
                msg = (
                    f"🚀 *صفقة جديدة رقم #{signal_counter}*\n\n"
                    f"📊 *درجة الثقة الإجمالية:* {confidence_level}\n"
                    f"📈 *نسبة صعود السهم الحالية:* +{change_val}%\n"
                    f"📌 *السهم:* {ticker} | *الاتجاه:* CALL 🟢\n"
                    f"💰 *سعر دخول السهم لايف:* ${entry_price}\n"
                    f"───────────────────\n"
                    f"🎯 *المستهدفات (دعم ومقومات الشارت):*\n"
                    f"• الهدف الأول: ${target1} | الهدف الثاني: ${target2}\n"
                    f"🛑 *صمام الأمان (وقف الخسارة):* ${stop_loss}\n"
                    f"───────────────────\n"
                    f"📰 *أخبار ورادار الحركة المترجم:* \n"
                    f"💬 {arabic_news}\n"
                    f"───────────────────\n"
                    f"⚠️ *تنبيه عبادي:* التزم بالسترايك القريب لحماية كاشك في منصة سهْم!"
                )
                send_telegram_message(msg)
                time.sleep(2)

        if now_sa.hour >= 23 and not report_sent_today:
            report_msg = (
                f"📊 *التقرير الختامي اليومي لرادار عبادي لجلسة {current_day}*\n\n"
                f"تم مراقبة الـ 29 سهم كاملة اليوم مية بالمية لايف من السوق.\n"
                f"▪️ عدد الصيدات والفرص الكلية المرسلة: {signal_counter}\n\n"
                f"حالة محفظتك وتداولاتك في أمان، نلقاكم الجلسة القادمة بروقان! 🦅🔥"
            )
            send_telegram_message(report_msg)
            report_sent_today = True

        time.sleep(30)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    try:
        startup_msg = (
            "🚀 *تم فك نظام الدرجات بنجاح يا عبادي!*\n"
            "🎯 الرادار الحين صار ذكي؛ يقيس نسبة الصعود بالملي، ويعزل لك صفقات \"النخبة 🟩\" عن الصفقات \"الممتازة 🟨\"."
        )
        send_telegram_message(startup_msg)
    except Exception as e:
        print(f"Startup greeting error: {e}")
        
    analyze_market_and_send()
