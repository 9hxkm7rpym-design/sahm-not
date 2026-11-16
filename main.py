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
        self.wfile.write(b"OK - Ultimate Professional Bot Connected!")
        
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
        volumes = [v for v in indicators.get('volume', []) if v is not None]
        
        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        latest_volume = volumes[-1] if volumes else 0
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
            "avg_candle": max(avg_candle_movement, 0.05),
            "volume_surge": latest_volume > (avg_volume * 1.05) 
        }
    except Exception as e:
        return {"success": False}

def calculate_real_chart_duration(current_price, target_price, avg_candle):
    distance = abs(target_price - current_price)
    estimated_candles = distance / avg_candle
    
    if estimated_candles <= 15:
        return f"خلال سياق لحظي سريع (متوقع خلال {round(estimated_candles)} إلى {round(estimated_candles*1.5)} دقيقة بناءً على الشارت)"
    elif estimated_candles <= 60:
        hours = round(estimated_candles / 60, 1)
        return f"خلال الجلسة الحالية (متوقع خلال {hours} إلى {round(hours*1.5, 1)} ساعة من الشارت)"
    elif estimated_candles <= 240:
        hours = round(estimated_candles / 60)
        return f"خلال ساعات التداول (متوقع خلال {hours} إلى {hours+2} ساعات)"
    else:
        days = round(estimated_candles / 390, 1)
        if days <= 1:
            return "خلال يوم تداول واحد (بناءً على مسافة الشارت)"
        elif days <= 2:
            return "خلال يوم إلى يومين (بناءً على مسافة الشارت)"
        else:
            return f"خلال {round(days)} أيام تقريباً (حسب حركة الشارت الفنية)"

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
            if not report_sent_today and len(active_trades) > 0 and ksa_time.time() >= dtime(0, 5):
                total_trades = daily_stats['wins'] + daily_stats['losses']
                win_rate = round((daily_stats['wins'] / total_trades) * 100, 1) if total_trades > 0 else 0
                summary_msg = (
                    f"📊 *تقرير أداء المحفظة الختامي*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ *الأهداف المحققة:* `{daily_stats['wins']}`\n"
                    f"❌ *وقف الخسارة:* `{daily_stats['losses']}`\n"
                    f"🎯 *نسبة النجاح الكلية:* `{win_rate}%`\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🦅 *تم إغلاق كافة الصفقات لتأمين الأرباح بنهاية الجلسة.*"
                )
                send_telegram_message(summary_msg)
                active_trades.clear()
                report_sent_today = True
                
            time.sleep(60)
            continue

        # 1. تتبع دقيق وصارم للأهداف ووقف الخسارة الفني
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
                        send_telegram_message(f"🎯 *هدف محقق باحترافية! (+)*\n• السهم: `{ticker}` | CALL\n• السعر الحالي: `${current_price}`\n• الحالة: تم تحقيق المستهدف الأول بنجاح ✅")
                        tickers_to_remove.append(ticker)
                    elif current_price <= stop_loss:
                        daily_stats["losses"] += 1
                        send_telegram_message(f"🛑 *وقف خسارة فني (-)*\n• السهم: `{ticker}` | CALL\n• السعر الحالي: `${current_price}`\n• الحالة: تم كسر القاع الفني وضرب وقف الخسارة ❌")
                        tickers_to_remove.append(ticker)
                elif trade_type == "PUT":
                    if current_price <= target1:
                        daily_stats["wins"] += 1
                        send_telegram_message(f"🎯 *هدف محقق باحترافية! (+)*\n• السهم: `{ticker}` | PUT\n• السعر الحالي: `${current_price}`\n• الحالة: تم تحقيق المستهدف الأول بنجاح ✅")
                        tickers_to_remove.append(ticker)
                    elif current_price >= stop_loss:
                        daily_stats["losses"] += 1
                        send_telegram_message(f"🛑 *وقف خسارة فني (-)*\n• السهم: `{ticker}` | PUT\n• السعر الحالي: `${current_price}`\n• الحالة: تم اختراق القمة الفنية وضرب وقف الخسارة ❌")
                        tickers_to_remove.append(ticker)
                        
        for t in tickers_to_remove:
            del active_trades[t]

        # 2. فحص ترند السوق العام (SPY)
        spy_market = get_real_market_data("SPY")
        market_trend = "NEUTRAL"
        if spy_market.get("success"):
            if spy_market["change"] > 0.1:
                market_trend = "BULLISH"
            elif spy_market["change"] < -0.1:
                market_trend = "BEARISH"

        # 3. اصطياد الفرص بمرونة عالية لضمان استمرار الصفقات اليومية الممتازة
        for ticker in WATCHLIST:
            if ticker in active_trades or ticker in sent_signals or ticker == "SPY":
                continue
                
            market = get_real_market_data(ticker)
            if market.get("success"):
                change_val = market["change"]
                current_price = market["price"]
                has_volume = market["volume_surge"]
                recent_low = market["recent_low"]
                recent_high = market["recent_high"]
                avg_candle = market["avg_candle"]
                
                if abs(change_val) >= 1.2 and has_volume:
                    
                    if abs(change_val) >= 2.0:
                        grade = "🔥 صفقة نخبة (درجة A+) - زخم سيولة قوي جداً"
                        is_elite = True  
                    else:
                        grade = "⭐ صفقة نشطة (درجة A) - حركة سعرية مؤكدة"
                        is_elite = False

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
                            f"📌 *السهم:* `{ticker}`\n"
                            f"📈 *النوع:* `CALL (صعود) 🟢`\n"
                            f"💵 *السعر الحالي:* `${current_price}` (+{change_val}%)\n"
                            f"🏆 *التقييم:* `{grade}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"🎯 *منطقة الدخول:* `${entry_min}` ⟵ `${entry_max}`\n"
                            f"🎯 *الأهداف:* `${target1}` | `${target2}`\n"
                            f"🛑 *وقف الخسارة الفني:* `${stop_loss}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⏳ *التقدير الزمني (مستخرج من الشارت):* `{dynamic_duration}`\n"
                            f"⚡ *ملاحظة:* صفقة مرنة ومدروسة لتوفير فرص يومية متجددة."
                        )
                        send_telegram_message(msg)
                        time.sleep(1)
                        
                    elif change_val < 0:
                        signal_counter += 1
                        entry_min = round(current_price * 0.998, 2)
                        entry_max = round(current_price * 1.002, 2)
                        target1 = round(current_price * 0.985, 2)
                        target2 = round(current_price * 0.975, 2)
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
                            f"📌 *السهم:* `{ticker}`\n"
                            f"📉 *النوع:* `PUT (هبوط) 🔴`\n"
                            f"💵 *السعر الحالي:* `${current_price}` ({change_val}%)\n"
                            f"🏆 *التقييم:* `{grade}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"🎯 *منطقة الدخول:* `${entry_min}` ⟵ `${entry_max}`\n"
                            f"🎯 *الأهداف:* `${target1}` | `${target2}`\n"
                            f"🛑 *وقف الخسارة الفني:* `${stop_loss}`\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⏳ *التقدير الزمني (مستخرج من الشارت):* `{dynamic_duration}`\n"
                            f"⚡ *ملاحظة:* صفقة مرنة ومدروسة لتوفير فرص يومية متجددة."
                        )
                        send_telegram_message(msg)
                        time.sleep(1)

        time.sleep(30)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    try:
        send_telegram_message("⚡ *تم تشغيل النسخة الاحترافية الكفو بنجاح! جاهز لاصطياد الفرص وتتبع الأهداف وتقرير نهاية الجلسة.*")
    except:
        pass
        
    analyze_market_and_send()
