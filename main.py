import os
import time
import requests
from datetime import datetime, timedelta
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- بيانات الربط المباشر المعتمدة لبوتك الجديد ---
TELEGRAM_TOKEN = "8472180858:AAG2eMBTuzRMz-tLkT2MV9ow_YjeUbXAbyY"
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
        self.wfile.write(b"Radar Club Sahm (CALL & PUT) Is Active!")

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
    abs_change = abs(change_val)
    if abs_change > 3.5:
        duration_text = "سريعة جداً (خلال ساعتين إلى نهاية جلسة اليوم)"
        expected_date = now_sa.strftime("%Y-%m-%d")
    elif abs_change > 2.0:
        duration_text = "متوسطة (خلال 24 ساعة - جلسة عمل القادمة)"
        target_date = now_sa + timedelta(days=1)
        if target_date.weekday() == 5: 
            target_date += timedelta(days=2)
        elif target_date.weekday() == 6: 
            target_date += timedelta(days=1)
        expected_date = target_date.strftime("%Y-%m-%d")
    else:
        duration_text = "موجة قصيرة (خلال يومين إلى 3 أيام عمل)"
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

        if current_weekday == 5 or current_weekday == 6:
            print(f"💤 الويكند بدأ.. الرادار مريح الحين يا عبادي.")
            time.sleep(3600)
            continue

        if current_time_float < 16.5 or current_time_float > 23.0:
            time.sleep(60)
            continue

        # --- مراقبة وتتبع صفقات الـ CALL والـ PUT لايف ---
        for ticker, trade in list(active_trades.items()):
            market = get_real_market_data(ticker)
            if market.get("success"):
                live_price = market["price"]
                
                # تتبع أهداف CALL (ربح بالصعود)
                if trade["type"] == "CALL":
                    if live_price >= trade["target1"]:
                        success_count += 1
                        msg = f"🎯 *صيدة ناجحة بالملي! سهم {ticker}*\n▪ *صفقة رقم:* #{trade['id']} (CALL) 🟢\n▪ *سعر الدخول:* ${trade['entry']}\n🔥 *السعر الحالي:* ${live_price}\n💰 جني أرباح فوري في محفظتك!"
                        send_telegram_message(msg)
                        active_trades.pop(ticker)
                    elif live_price <= trade["stop_loss"]:
                        failed_count += 1
                        msg = f"🛑 *تنبيه الوقف - سهم {ticker}*\n▪ *صفقة رقم:* #{trade['id']} (CALL) 🟢\n⚠️ ضرب وقف الخسارة (${trade['stop_loss']}) لتأمين كاشك."
                        send_telegram_message(msg)
                        active_trades.pop(ticker)
                        
                # تتبع أهداف PUT (ربح بالهبوط)
                elif trade["type"] == "PUT":
                    if live_price <= trade["target1"]:
                        success_count += 1
                        msg = f"🎯 *صيدة ناجحة بالملي! سهم {ticker}*\n▪ *صفقة رقم:* #{trade['id']} (PUT) 🔴\n▪ *سعر الدخول:* ${trade['entry']}\n🔥 *السعر الحالي المنهار:* ${live_price}\n💰 نقش الغنايم وأرباح الـ PUT يا عبادي!"
                        send_telegram_message(msg)
                        active_trades.pop(ticker)
                    elif live_price >= trade["stop_loss"]:
                        failed_count += 1
                        msg = f"🛑 *تنبيه الوقف - سهم {ticker}*\n▪ *صفقة رقم:* #{trade['id']} (PUT) 🔴\n⚠️ ضرب وقف الخسارة (${trade['stop_loss']}) لسلامة المحفظة الحين."
                        send_telegram_message(msg)
                        active_trades.pop(ticker)

        # --- فحص الأسواق واقتناص الفرص (CALL & PUT) ---
        for ticker in WATCHLIST:
            if ticker in active_trades or ticker in sent_signals:
                continue
                
            market = get_real_market_data(ticker)
            if market.get("success"):
                change_val = market["change"]
                entry_price = market["price"]
                
                # 🟩 شروط الـ CALL (صعود السهم)
                if change_val > 1.5:
                    signal_counter += 1
                    confidence_level = "قوية جداً (النخبة 🟩)" if change_val > 3.0 else "تأكيد صعود (درجة ممتازة 🟨)"
                    target1 = round(entry_price * 1.01, 2)
                    target2 = round(entry_price * 1.02, 2)
                    stop_loss = round(entry_price * 0.97, 2)
                    duration, target_date_str = calculate_time_target(change_val, now_sa)
                    
                    active_trades[ticker] = {
                        "id": signal_counter, "type": "CALL", "entry": entry_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    arabic_news = translate_and_summarize_news(ticker, confidence_level)
                    
                    msg = (
                        f"🚀 *صفقة جديدة رقم #{signal_counter}*\n\n"
                        f"📊 *درجة الثقة:* {confidence_level}\n"
                        f"📈 *نسبة الحركة:* +{change_val}%\n"
                        f"📌 *السهم:* {ticker} | *الاتجاه:* CALL 🟢\n"
                        f"💰 *سعر دخول السهم:* ${entry_price}\n"
                        f"───────────────────\n"
                        f"🎯 *المستهدفات:*\n"
                        f"• الهدف الأول: ${target1} | الهدف الثاني: ${target2}\n"
                        f"🛑 *صمام الأمان (الوقف):* ${stop_loss}\n"
                        f"───────────────────\n"
                        f"⏳ *المدى المتوقع للهدف:* {duration}\n"
                        f"📅 *التاريخ المستهدف بالملي:* {target_date_str}\n"
                        f"───────────────────\n"
                        f"💬 {arabic_news}"
                    )
                    send_telegram_message(msg)
                    time.sleep(2)
                    
                # 🔴 شروط الـ PUT (هبوط السهم)
                elif change_val < -1.5:
                    signal_counter += 1
                    confidence_level = "انهيار قوي (النخبة 🟥)" if change_val < -3.0 else "تأكيد هبوط (درجة ممتازة 🟪)"
                    # حساب أهداف الـ PUT تحت السعر الحالي، والوقف فوقه
                    target1 = round(entry_price * 0.99, 2)
                    target2 = round(entry_price * 0.98, 2)
                    stop_loss = round(entry_price * 1.03, 2)
                    duration, target_date_str = calculate_time_target(change_val, now_sa)
                    
                    active_trades[ticker] = {
                        "id": signal_counter, "type": "PUT", "entry": entry_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    arabic_news = translate_and_summarize_news(ticker, confidence_level)
                    
                    msg = (
                        f"💥 *صفقة عكسية جديدة رقم #{signal_counter}*\n\n"
                        f"📊 *درجة الثقة:* {confidence_level}\n"
                        f"📉 *نسبة الهبوط:* {change_val}%\n"
                        f"📌 *السهم:* {ticker} | *الاتجاه:* PUT 🔴\n"
                        f"💰 *سعر دخول السهم:* ${entry_price}\n"
                        f"───────────────────\n"
                        f"🎯 *المستهدفات (عقود الهبوط):*\n"
                        f"• الهدف الأول: ${target1} | الهدف الثاني: ${target2}\n"
                        f"🛑 *صمام الأمان (الوقف فوق السعر):* ${stop_loss}\n"
                        f"───────────────────\n"
                        f"⏳ *المدى المتوقع للهدف:* {duration}\n"
                        f"📅 *التاريخ المستهدف بالملي:* {target_date_str}\n"
                        f"───────────────────\n"
                        f"💬 {arabic_news}"
                    )
                    send_telegram_message(msg)
                    time.sleep(2)

        if now_sa.hour >= 23 and not report_sent_today:
            running_now = len(active_trades)
            report_msg = (
                f"📊 *التقرير الختامي اليومي لرادار عبادي لجلسة {current_day}*\n\n"
                f"🎯 *حصاد الصيدات والنتائج اليومية (CALL & PUT):*\n"
                f"▪️ إجمالي الفرص المرسلة كاملة: {signal_counter}\n"
                f"✅ عدد الصفقات الناجحة: {success_count} 🔥\n"
                f"🛑 عدد الصفقات الخاسرة: {failed_count}\n"
                f"⏳ صفقات مستمرة للجلسة القادمة: {running_now}\n"
                f"───────────────────\n"
                f"حالة محفظتك وتداولاتك في أمان يا بطل! 🦅🔥"
            )
            send_telegram_message(report_msg)
            report_sent_today = True

        time.sleep(30)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    try:
        startup_msg = (
            "🦅 *تم تدشين رادار كلوب المطور (CALL & PUT) بنجاح!*\n"
            "🎯 البوت الحين بيفحص الاتجاهين لايف؛ الصعود والهبوط بالمدى الزمني الدقيق!"
        )
        send_telegram_message(startup_msg)
    except Exception as e:
        print(f"Startup greeting error: {e}")
        
    analyze_market_and_send()
