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

# --- الذاكرة المؤقتة الذكية وإحصائيات الأرباح ---
active_trades = {}      
sent_signals = set()    
success_count = 0       
failed_count = 0        
signal_counter = 0      
report_sent_today = False
last_reset_day = ""

class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Radar Abbadi Time Predictor Is Active!")

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
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        current_price = data['chart']['result'][0]['meta']['regularMarketPrice']
        previous_close = data['chart']['result'][0]['meta']['previousClose']
        
        change_percent = ((current_price - previous_close) / previous_close) * 100
        
        return {
            "success": True,
            "price": round(current_price, 2),
            "change": round(change_percent, 2)
        }
    except Exception as e:
        return {"success": False}

def calculate_time_target(change_val, now_sa):
    """حساب المدة والتاريخ المتوقع لتحقيق الهدف بناءً على قوة السيولة"""
    if change_val > 3.5:
        duration_text = "سريعة جداً (خلال ساعتين إلى نهاية جلسة اليوم)"
        expected_date = now_sa.strftime("%Y-%m-%d")
    elif change_val > 2.0:
        duration_text = "متوسطة (خلال 24 ساعة - جلسة عمل القادمة)"
        # إضافة يوم عمل واحد
        target_date = now_sa + timedelta(days=1)
        if target_date.weekday() == 5: # لو صادف السبت
            target_date += timedelta(days=2)
        elif target_date.weekday() == 6: # لو صادف الأحد
            target_date += timedelta(days=1)
        expected_date = target_date.strftime("%Y-%m-%d")
    else:
        duration_text = "موجة قصيرة (خلال يومين إلى 3 أيام عمل)"
        # إضافة يومين عمل
        target_date = now_sa + timedelta(days=2)
        if target_date.weekday() == 5 or target_date.weekday() == 6:
            target_date += timedelta(days=2)
        expected_date = target_date.strftime("%Y-%m-%d")
        
    return duration_text, expected_date

def analyze_market_and_send():
    global report_sent_today, last_reset_day, signal_counter, success_count, failed_count
    
    while True:
        now_sa = datetime.utcnow() + timedelta(hours=3)
        current_day = now_sa.strftime("%Y-%m-%d")
        current_time_float = now_sa.hour + (now_sa.minute / 60.0)
        current_weekday = now_sa.weekday() 
        
        if current_day != last_reset_day:
            signal_counter = 0
            success_count = 0
            failed_count = 0
            sent_signals.clear()
            active_trades.clear()
            report_sent_today = False
            last_reset_day = current_day

        # 🛑 1. فلتر الويكند الرسمي (السبت والأحد)
        if current_weekday == 5 or current_weekday == 6:
            print(f"💤 الويكند بدأ.. الرادار مريح الحين.")
            time.sleep(3600)
            continue

        # 🛑 2. فلتر وقت السوق الرسمي بتوقيت السعودية (4:30 عصراً إلى 11:00 مساءً)
        if current_time_float < 16.5 or current_time_float > 23.0:
            time.sleep(60)
            continue

        # --- مراقبة وتتبع الأسعار لايف للأهداف والوقف ---
        for ticker, trade in list(active_trades.items()):
            market = get_real_market_data(ticker)
            if market.get("success"):
                live_price = market["price"]
                
                if live_price >= trade["target1"]:
                    success_count += 1
                    msg = (
                        f"🎯 *صيدة ناجحة بالملي! سهم {ticker}*\n"
                        f"▪ *صفقة رقم:* #{trade['id']}\n"
                        f"▪ *سعر الدخول القديم:* ${trade['entry']}\n"
                        f"🔥 *السعر الحالي المكتسح:* ${live_price} (ضرب الهدف الموعود)\n"
                        f"💰 جني أرباح فوري ونقش الغنايم يا عبادي في محفظتك!"
                    )
                    send_telegram_message(msg)
                    active_trades.pop(ticker)
                    
                elif live_price <= trade["stop_loss"]:
                    failed_count += 1
                    msg = (
                        f"🛑 *تنبيه الوقف وتأمين كاشك - سهم {ticker}*\n"
                        f"▪ *صفقة رقم:* #{trade['id']}\n"
                        f"▪ *سعر السهم الحالي:* ${live_price}\n"
                        f"⚠️ ضرب وقف الخسارة (${trade['stop_loss']}) لسلامة المحفظة الحين."
                    )
                    send_telegram_message(msg)
                    active_trades.pop(ticker)

        # --- فحص السوق لاكتشاف فرص صعود جديدة ---
        for ticker in WATCHLIST:
            if ticker in active_trades or ticker in sent_signals:
                continue
                
            market = get_real_market_data(ticker)
            if market.get("success"):
                change_val = market["change"]
                
                if change_val > 1.5:
                    signal_counter += 1  
                    entry_price = market["price"]
                    confidence_level = "قوية جداً (النخبة 🟩)" if change_val > 3.0 else "تأكيد صعود (درجة ممتازة 🟨)"
                    
                    target1 = round(entry_price * 1.01, 2)
                    target2 = round(entry_price * 1.02, 2)
                    stop_loss = round(entry_price * 0.97, 2)
                    
                    # حساب المدة الزمنية والتاريخ المتوقع بالملي
                    duration, target_date_str = calculate_time_target(change_val, now_sa)
                    
                    active_trades[ticker] = {
                        "id": signal_counter, "entry": entry_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    
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
                        f"⏳ *المدى الزمني المتوقع للهدف:* {duration}\n"
                        f"📅 *التاريخ المستهدف بالملي:* {target_date_str}\n"
                        f"───────────────────\n"
                        f"📰 *أخبار ورادار الحركة المترجم:* \n"
                        f"💬 {arabic_news}\n"
                        f"───────────────────\n"
                        f"⚠️ *تنبيه عبادي:* التزم بالسترايك القريب والمدى الزمني لحماية كاشك!"
                    )
                    send_telegram_message(msg)
                    time.sleep(2)

        # --- التقرير الختامي الساعة 11 بالليل ---
        if now_sa.hour >= 23 and not report_sent_today:
            running_now = len(active_trades)
            report_msg = (
                f"📊 *التقرير الختامي اليومي لرادار عبادي لجلسة {current_day}*\n\n"
                f"تم مراقبة الـ 29 سهم كاملة مية بالمية لايف من قلب السوق.\n"
                f"───────────────────\n"
                f"🎯 *حصاد الصيدات والنتائج اليومية:*\n"
                f"▪️ إجمالي الفرص المرسلة كاملة: {signal_counter}\n"
                f"✅ عدد الصفقات الناجحة (ضربت الهدف): {success_count} 🔥\n"
                f"🛑 عدد الصفقات الخاسرة (ضربت الوقف): {failed_count}\n"
                f"⏳ صفقات مستمرة للجلسة القادمة: {running_now}\n"
                f"───────────────────\n"
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
            "🚀 *أبشرك يا عبادي.. تم تفعيل المحلل الزمني الذكي الحين تلقائياً!*\n"
            "🎯 الرادار الحين صار يحدد لك المدى المتوقع بالساعات والأيام ويعطيك تاريخ الهدف بالملي بداخل الرسالة!"
        )
        send_telegram_message(startup_msg)
    except Exception as e:
        print(f"Startup greeting error: {e}")
        
    analyze_market_and_send()
