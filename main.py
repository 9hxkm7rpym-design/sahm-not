import os
import time
import requests
import yfinance as yf
from datetime import datetime, timedelta
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==================== إعدادات تليجرام ====================
TELEGRAM_TOKEN = "8472180858:AAG2eMBTuzRMz-tLkT2MV9ow_YjeUbXAbyY"
CHAT_ID = "1068286006"

# ==================== قائمة الـ 29 سهم المعتمدة ====================
WATCHLIST = [
    "NVDA", "TSLA", "MSFT", "AMZN", "AAPL", "META", "OXY", "NFLX", "AMD", "GOOGL",
    "BA", "BABA", "COIN", "DIS", "JPM", "MARA", "NIO", "ORCL", "PLTR", "QQQ",
    "ROKU", "SPY", "SQ", "UBER", "V", "WMT", "XOM", "PFE", "SOFI"
]

# ==================== الذاكرة المؤقتة وإحصائيات الأرباح ====================
active_trades = {}      
sent_signals = set()    
success_count = 0       
failed_count = 0        
signal_counter = 0      
report_sent_today = False
last_reset_day = ""

successful_tickers = []
failed_tickers = []

# ==================== سيرفر ويب لتجنب مشاكل رندر ====================
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Radar Club Master Pro Bot Is Running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

def send_telegram_message(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error sending message: {e}")

def answer_callback_query(callback_query_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "text": text, "show_alert": True}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error answering callback: {e}")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_market_data(ticker):
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # الاعتماد على فريم الساعة (1h) لتحليل صفقات اليوم الواحد
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="5d", interval="1h")
        
        if df.empty or len(df) < 20:
            return {"success": False}
            
        current_price = float(df['Close'].iloc[-1])
        previous_close = float(df['Close'].iloc[-2])
        change_percent = ((current_price - previous_close) / previous_close) * 100
        
        current_volume = float(df['Volume'].iloc[-1])
        avg_volume = float(df['Volume'].mean())
        rsi_value = calculate_rsi(df['Close'])
        
        return {
            "success": True,
            "price": round(current_price, 2),
            "prev_close": round(previous_close, 2),
            "change": round(change_percent, 2),
            "volume": current_volume,
            "avg_volume": round(avg_volume, 0),
            "rsi": round(rsi_value, 1)
        }
    except Exception as e:
        return {"success": False}

def check_telegram_updates():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url, timeout=35)
            if response.status_code == 200:
                data = response.json()
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    
                    if "callback_query" in result:
                        query = result["callback_query"]
                        query_id = query["id"]
                        data_str = query["data"]
                        
                        if data_str.startswith("update_"):
                            ticker = data_str.split("_")[1]
                            market = get_market_data(ticker)
                            if market.get("success"):
                                price = market["price"]
                                change = market["change"]
                                rsi = market["rsi"]
                                msg = f"📌 السهم: {ticker}\n💵 السعر الحالي: ${price}\n⚡ التغير: {change}%\n📊 RSI: {rsi}"
                                answer_callback_query(query_id, msg)
                            else:
                                answer_callback_query(query_id, f"تعذر جلب سعر {ticker} حالياً.")
        except Exception as e:
            print(f"Error in telegram updates: {e}")
        time.sleep(1)

def analyze_market_and_send():
    global report_sent_today, last_reset_day, signal_counter, success_count, failed_count, successful_tickers, failed_tickers
    
    while True:
        now_sa = datetime.utcnow() + timedelta(hours=3)
        current_day = now_sa.strftime("%Y-%m-%d")
        current_time_float = now_sa.hour + (now_sa.minute / 60.0)
        current_weekday = now_sa.weekday() 
        
        if current_day != last_reset_day:
            signal_counter = 0
            success_count = 0
            failed_count = 0
            successful_tickers.clear()
            failed_tickers.clear()
            sent_signals.clear()
            active_trades.clear()
            report_sent_today = False
            last_reset_day = current_day

        if current_weekday == 5 or current_weekday == 6:
            time.sleep(3600)
            continue

        if current_time_float < 16.5 or current_time_float > 23.0:
            time.sleep(60)
            continue

        # --- مراقبة صفقات الـ CALL والـ PUT لايف طوال جلسة اليوم ---
        for ticker, trade in list(active_trades.items()):
            market = get_market_data(ticker)
            if market.get("success"):
                live_price = market["price"]
                
                if trade["type"] == "CALL":
                    if live_price >= trade["target1"]:
                        success_count += 1
                        successful_tickers.append(f"{ticker} (CALL 🟢)")
                        send_telegram_message(f"🎯 *هدف محقق بامتياز! سهم {ticker}*\n▪ صفقة رقم #{trade['id']} (CALL) 🟢\n▪ السعر الحالي: ${live_price}")
                        active_trades.pop(ticker)
                    elif live_price <= trade["stop_loss"]:
                        failed_count += 1
                        failed_tickers.append(f"{ticker} (CALL 🟢)")
                        send_telegram_message(f"🛑 *ضرب وقف الخسارة - سهم {ticker}*\n▪ صفقة رقم #{trade['id']} (CALL) 🟢")
                        active_trades.pop(ticker)
                        
                elif trade["type"] == "PUT":
                    if live_price <= trade["target1"]:
                        success_count += 1
                        successful_tickers.append(f"{ticker} (PUT 🔴)")
                        send_telegram_message(f"🎯 *هدف محقق بامتياز! سهم {ticker}*\n▪ صفقة رقم #{trade['id']} (PUT) 🔴\n▪ السعر الحالي: ${live_price}")
                        active_trades.pop(ticker)
                    elif live_price >= trade["stop_loss"]:
                        failed_count += 1
                        failed_tickers.append(f"{ticker} (PUT 🔴)")
                        send_telegram_message(f"🛑 *ضرب وقف الخسارة - سهم {ticker}*\n▪ صفقة رقم #{trade['id']} (PUT) 🔴")
                        active_trades.pop(ticker)

        # --- مسح السوق وتصنيف الصفقات مع الشرح الرياضي ---
        for ticker in WATCHLIST:
            if ticker in active_trades or ticker in sent_signals:
                continue
                
            market = get_market_data(ticker)
            if market.get("success"):
                entry_price = market["price"]
                prev_close = market["prev_close"]
                change_val = market["change"]
                volume = market["volume"]
                avg_vol = market["avg_volume"]
                rsi = market["rsi"]
                
                vol_ratio = volume / avg_vol if avg_vol > 0 else 1.0

                grade = ""
                signal_type = ""

                # 👑 1. الدرجة الأولى: الملكي الفاخر (⭐⭐⭐)
                if abs(change_val) >= 2.0 and vol_ratio >= 1.5:
                    grade = "الدرجة الأولى (الملكي الفاخر ⭐⭐⭐)"
                    signal_type = "CALL" if change_val > 0 else "PUT"

                # 🔥 2. الدرجة الثانية: النشط والسريع (⭐⭐)
                elif abs(change_val) >= 1.2 and vol_ratio >= 1.2:
                    grade = "الدرجة الثانية (النشط والسريع ⭐⭐)"
                    signal_type = "CALL" if change_val > 0 else "PUT"

                # ⚡ 3. الدرجة الثالثة: المضاربي اللحظي (⭐)
                elif abs(change_val) >= 0.8 and vol_ratio >= 1.05:
                    grade = "الدرجة الثالثة (المضاربي اللحظي ⭐)"
                    signal_type = "CALL" if change_val > 0 else "PUT"

                if grade and signal_type:
                    signal_counter += 1
                    
                    if signal_type == "CALL":
                        entry_low = round(entry_price * 0.998, 2)
                        entry_high = round(entry_price * 1.002, 2)
                        target1 = round(entry_price * 1.025, 2)
                        target2 = round(entry_price * 1.05, 2)
                        stop_loss = round(entry_price * 0.982, 2)
                        icon = "🟢"
                        title_emoji = "🔥"
                    else:
                        entry_low = round(entry_price * 0.998, 2)
                        entry_high = round(entry_price * 1.002, 2)
                        target1 = round(entry_price * 0.975, 2)
                        target2 = round(entry_price * 0.95, 2)
                        stop_loss = round(entry_price * 1.018, 2)
                        icon = "🔴"
                        title_emoji = "🩸"

                    active_trades[ticker] = {
                        "id": signal_counter, "type": signal_type, "entry": entry_price,
                        "target1": target1, "stop_loss": stop_loss
                    }
                    sent_signals.add(ticker)
                    
                    explanation_text = (
                        f"• ⚡ *نسبة التغير ({change_val}%):* حُسبت بقانون (السعر الحالي ${entry_price} - إغلاق أمس ${prev_close}) ÷ إغلاق أمس × 100 على فريم الساعة.\n"
                        f"• 🌊 *حجم السيولة ({int(volume):,} مقابل متوسط {int(avg_vol):,}):* حُسبت بمقارنة حجم التداول الحالي بمتوسط آخر 5 أيام ووجدنا أنه يمثل ({round(vol_ratio, 1)}x) من المعتاد.\n"
                        f"• 📊 *مؤشر القوة (RSI: {rsi}):* حُسب بمتوسط سرعة الصعود والهبوط لآخر 14 شمعة على فريم الساعة."
                    )

                    msg = (
                        f"{title_emoji} *صفقة أوبشن يومية [{signal_type}] - {grade}* {icon}\n\n"
                        f"📌 *رقم الصفقة:* `#{signal_counter}`\n"
                        f"📌 *الرمز:* `{ticker}` | *الاتجاه:* `{signal_type} {icon}`\n"
                        f"💵 *السعر الحالي:* `${entry_price}`\n\n"
                        f"🧮 *كيف عرفنا وحسبنا المؤشرات؟ (كشف الهود):*\n"
                        f"{explanation_text}\n\n"
                        f"🎯 *منطقة الدخول الآمنة:* `${entry_low} - ${entry_high}`\n"
                        f"• الهدف الأول: `${target1}` {icon}\n"
                        f"• الهدف الثاني: `${target2}` 🎯\n"
                        f"• وقف الخسارة: `${stop_loss}` 🛑"
                    )
                    
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": f"🔄 تحديث سعر {ticker} لايف", "callback_data": f"update_{ticker}"}]
                        ]
                    }
                    send_telegram_message(msg, reply_markup=keyboard)
                    time.sleep(2)

        # --- التقرير الختامي اليومي عند إغلاق السوق ---
        if now_sa.hour >= 23 and not report_sent_today:
            success_str = ", ".join(successful_tickers) if successful_tickers else "لا توجد"
            failed_str = ", ".join(failed_tickers) if failed_tickers else "لا توجد"
            report_msg = (
                f"📊 *التقرير الختامي اليومي لرادار عبادي ({current_day})*\n\n"
                f"▪ إجمالي الفرص المرسلة: {signal_counter}\n"
                f"✅ الأهداف المحققة: {success_str}\n"
                f"🛑 وقف الخسارة: {failed_str}\n"
            )
            send_telegram_message(report_msg)
            report_sent_today = True

        time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=check_telegram_updates, daemon=True).start()
    send_telegram_message("🦅 *رادار عبادي يعمل الآن بكامل طاقته (الدرجات + الشرح التعليمي + فريم الساعة)!*")
    analyze_market_and_send()
