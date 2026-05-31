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
active_trades = {}      # لمراقبة الصفقات المفتوحة لايف
sent_signals = set()    # لمنع التكرار اليومي للسهم
success_count = 0       # عداد الصفقات الناجحة
failed_count = 0        # عداد صفقات الوقف
signal_counter = 0      
report_sent_today = False
last_reset_day = ""

class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Radar Abbadi Live Tracking Is Active!")

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
    """جلب الأسعار الحقيقية وحساب الفلترة بدقة بالدرجات"""
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

def analyze_market_and_send():
    global report_sent_today, last_reset_day, signal_counter, success_count, failed_count
    
    while True:
        now_sa = datetime.utcnow() + timedelta(hours=3)
        current_day = now_sa.strftime("%Y-%m-%d")
        current_time_float = now_sa.hour + (now_sa.minute / 60.0)
        
        # 🔄 تصفير العدادات والذاكرة مع بداية يوم جديد
        if current_day != last_reset_day:
            signal_counter = 0
            success_count = 0
            failed_count = 0
            sent_signals.clear()
            active_trades.clear()
            report_sent_today = False
            last_reset_day = current_day

        # 🛑 فلتر وقت السوق الرسمي بتوقيت السعودية (4:30 عصراً إلى 11:00 مساءً)
        if current_time_float < 16.5 or current_time_float > 23.0:
            time.sleep(60)
            continue

        # 1️⃣ أولاً: مراقبة وتتبع الأسعار لايف للصفقات المفتوحة
        for ticker, trade in list(active_trades.items()):
            market = get_real_market_data(ticker)
            if market.get("success"):
                live_price = market["price"]
                
                # 🎉 فحص تحقق الهدف الأول
                if live_price >= trade["target1"]:
                    success_count += 1
                    msg = (
                        f"🎯 *صيدة ناجحة بالملي! سهم {ticker}*\n"
                        f"▪️ صفقة رقم: #{trade['id']}\n"
                        f"▪️ سعر الدخول: ${trade['entry']}\n"
                        f"🔥 *السعر الحالي وصل:* ${live_price} (ضرب الهدف الأول)\n"
                        f"💰 جني أرباح فوري يا عبادي على منصة سهْم بروقان!"
                    )
                    send_telegram_message(msg)
                    active_trades.pop(ticker) # إغلاق وتخريج الصفقة من المراقبة
                    
                # 🛑 فحص ضرب وقف الخسارة
                elif live_price <= trade["stop_loss"]:
                    failed_count += 1
                    msg = (
                        f"🛑 *تنبيه الوقف وتأمين رأس المال - سهم {ticker}*\n"
                        f"▪️ صفقة رقم: #{trade['id']}\n"
                        f"▪️ سعر السهم الحالي: ${live_price}\n"
                        f"⚠️ السعر ضرب وقف الخسارة (${trade['stop_loss']}) لتأمين كاشك من التقلب."
                    )
                    send_telegram_message(msg)
                    active_trades.pop(ticker)

        # 2️⃣ ثانياً: فحص السوق لاكتشاف فرص صعود جديدة
        for ticker in WATCHLIST:
            # إذا السهم عنده صفقة مفتوحة الحين نخليه يراقبها وما يفتح ثانية
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
                    
                    # حفظ الصفقة في قائمة التتبع النشط والفرص المرسلة
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
                        f"📰 *أخبار ورادار الحركة المترجم:* \n"
                        f"💬 {arabic_news}\n"
                        f"───────────────────\n"
                        f"⚠️ *تنبيه عبادي:* التزم بالسترايك القريب لحماية كاشك في منصة سهْم!"
                    )
                    send_telegram_message(msg)
                    time.sleep(2)

        # 3️⃣ ثالثاً: قفل التقرير الختامي الذكي بالإحصائيات الساعة 11 بالليل
        if now_sa.hour >= 23 and not report_sent_today:
            # حساب الصفقات اللي لسه ما قفلت مع جرس الإغلاق
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

        time.sleep(30) # جولة فحص وتحديث للأسعار والأهداف كل 30 ثانية

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    try:
        startup_msg = (
            "🚀 *أبشرك يا عبادي.. تم تفعيل الرد الآلي وتتبع الأهداف لايف الحين!*\n"
            "🎯 الرادار الحين جالس يراقب أهداف ووقف الـ 29 سهم بالملي، وبيبشرك بكل صيدة ناجحة فوراً على الجوال!"
        )
        send_telegram_message(startup_msg)
    except Exception as e:
        print(f"Startup greeting error: {e}")
        
    analyze_market_and_send()
