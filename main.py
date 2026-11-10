import os
import time
import requests
from datetime import datetime, timedelta
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import yfinance as yf
import pandas as pd

# ==========================================
# 🚀 رادار النخبة الشامل (تجربة فورية مباشرة بدون شروط)
# ==========================================
TELEGRAM_TOKEN = "8472180858:AAG2eMBTuzRMz-tLkT2MV9ow_YjeUbXAbyY"
CHAT_ID = "1068286006"

WATCHLIST = [
    "NVDA", "TSLA", "AAPL", "AMZN", "MSFT", "META", "AMD", "MU", "NFLX", "GOOGL",
    "INTC", "PLTR", "COIN", "SMCI", "MARA", "SOFI", "HOOD", "OXY", "BA", "BABA",
    "DIS", "JPM", "QQQ", "SPY", "ROKU", "SQ", "UBER", "V", "WMT", "PFE"
]

TIMEFRAME = "5m"  
active_trades = {}      
sent_signals = set()    
success_count = 0       
failed_count = 0        
signal_counter = 0      
report_sent_today = False
last_reset_day = ""

successful_tickers = []
failed_tickers = []

class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Ultimate Test Options Radar Active!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        print("Telegram Response:", response.text) # طباعة الاستجابة في الكونسول للتحقق
    except Exception as e:
        print(f"Error sending message: {e}")

def get_live_price(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        return round(data['chart']['result'][0]['meta']['regularMarketPrice'], 2)
    except Exception as e:
        return None

def fetch_chart_data(ticker):
    try:
        df = yf.download(ticker, period="2d", interval=TIMEFRAME, progress=False)
        if df is None or df.empty or len(df) < 30:
            return None
        return df
    except Exception as e:
        return None

def calculate_indicators(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    return df

def send_forced_test_signal():
    """إرسال صفقة تجريبية مباشرة للتأكد من وصولها"""
    msg = (
        f"🧪 *[صفقة تجريبية حية مباشرة]* 🧪\n"
        f"🚀 *صفقة CALL مكثفة #TEST* 🚀\n"
        f"📌 السهم: `NVDA` | فريم: `5m`\n"
        f"⏳ مدة العقد المقترحة: *عقود نفس اليوم (0DTE - تنتهي اليوم)*\n"
        f"💵 الدخول: `135.50$` | الوقف (قاع الشمعة): `134.80$`\n"
        f"🎯 الهدف: `136.55$` (RR 1.5)\n"
        f"⚡ RVOL: `1.75x` | RSI: `55.4`\n"
        f"───────────────────\n"
        f"✅ السيرفر يقدح والتليجرام شغال 100%!"
    )
    send_telegram_message(msg)

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

        if current_time_float < 17.5 or current_time_float > 24.0:
            time.sleep(60)
            continue

        # --- 1. تتبع الصفقات المفتوحة لايف ---
        for ticker, trade in list(active_trades.items()):
            live_price = get_live_price(ticker)
            if live_price:
                if trade["type"] == "CALL":
                    if live_price >= trade["target"]:
                        success_count += 1
                        successful_tickers.append(f"{ticker} (CALL 🟢)")
                        msg = f"🎯 *صيدة ناجحة بالملي! سهم {ticker}*\n▪ صفقة رقم: #{trade['id']} (CALL) 🟢\n▪ سعر الدخول: ${trade['entry']}\n🔥 السعر الحالي: ${live_price}\n💰 جني أرباح فوري!"
                        send_telegram_message(msg)
                        active_trades.pop(ticker)
                    elif live_price <= trade["stop_loss"]:
                        failed_count += 1
                        failed_tickers.append(f"{ticker} (CALL 🟢)")
                        msg = f"🛑 *وقف الخسارة الفني - سهم {ticker}*\n▪ صفقة رقم: #{trade['id']} (CALL) 🟢\n⚠ ضرب قاع الوقف (${trade['stop_loss']})."
                        send_telegram_message(msg)
                        active_trades.pop(ticker)
                        
                elif trade["type"] == "PUT":
                    if live_price <= trade["target"]:
                        success_count += 1
                        successful_tickers.append(f"{ticker} (PUT 🔴)")
                        msg = f"🎯 *صيدة ناجحة بالملي! سهم {ticker}*\n▪ صفقة رقم: #{trade['id']} (PUT) 🔴\n▪ سعر الدخول: ${trade['entry']}\n🔥 السعر الحالي: ${live_price}\n💰 أرباح الـ PUT!"
                        send_telegram_message(msg)
                        active_trades.pop(ticker)
                    elif live_price >= trade["stop_loss"]:
                        failed_count += 1
                        failed_tickers.append(f"{ticker} (PUT 🔴)")
                        msg = f"🛑 *وقف الخسارة الفني - سهم {ticker}*\n▪ صفقة رقم: #{trade['id']} (PUT) 🔴\n⚠️ ضرب قمة الوقف (${trade['stop_loss']})."
                        send_telegram_message(msg)
                        active_trades.pop(ticker)

        # --- 2. فحص الأسهم وإرسال الإشارات الفعلية ---
        for ticker in WATCHLIST:
            if ticker in active_trades:
                continue
                
            df = fetch_chart_data(ticker)
            if df is None:
                continue
            
            try:
                df = calculate_indicators(df)
                prev = df.iloc[-2]
                
                high = prev['High']
                low = prev['Low']
                close = prev['Close']
                open_p = prev['Open']
                
                rsi = prev['RSI']
                macd = prev['MACD']
                sig = prev['Signal_Line']
                vwap = prev['VWAP']
                
                avg_vol = df['Volume'].tail(10).mean()
                rvol = prev['Volume'] / avg_vol if avg_vol > 0 else 1
                
                is_call = (close > open_p) and (close > vwap) and (macd > sig) and (rvol >= 1.0)
                is_put = (close < open_p) and (close < vwap) and (macd < sig) and (rvol >= 1.0)
                
                contract_duration = "عقود نفس اليوم (0DTE - تنتهي اليوم)" if ticker in ["SPY", "QQQ", "NVDA", "TSLA", "AAPL", "AMZN", "MSFT"] else "عقود قصيرة (1 إلى 2 أيام)"
                
                if is_call:
                    signal_counter += 1
                    entry_price = round(close, 2)
                    stop_loss = round(low - 0.05, 2)
                    risk = round(entry_price - stop_loss, 2)
                    
                    if risk > 0:
                        target = round(entry_price + (risk * 1.5), 2)
                        active_trades[ticker] = {
                            "id": signal_counter, "type": "CALL", "entry": entry_price,
                            "target": target, "stop_loss": stop_loss
                        }
                        
                        msg = (
                            f"🚀 *صفقة CALL مكثفة #{signal_counter}* 🚀\n"
                            f"📌 السهم: `{ticker}` | فريم: `5m`\n"
                            f"⏳ مدة العقد المقترحة: *{contract_duration}*\n"
                            f"💵 الدخول: `{entry_price}$` | الوقف (قاع الشمعة): `{stop_loss}$`\n"
                            f"🎯 الهدف: `{target}$` (RR 1.5)\n"
                            f"⚡ RVOL: `{rvol:.2f}x` | RSI: `{rsi:.1f}`"
                        )
                        send_telegram_message(msg)
                        time.sleep(1)
                        
                elif is_put:
                    signal_counter += 1
                    entry_price = round(close, 2)
                    stop_loss = round(high + 0.05, 2)
                    risk = round(stop_loss - entry_price, 2)
                    
                    if risk > 0:
                        target = round(entry_price - (risk * 1.5), 2)
                        active_trades[ticker] = {
                            "id": signal_counter, "type": "PUT", "entry": entry_price,
                            "target": target, "stop_loss": stop_loss
                        }
                        
                        msg = (
                            f"💥 *صفقة PUT مكثفة #{signal_counter}* 💥\n"
                            f"📌 السهم: `{ticker}` | فريم: `5m`\n"
                            f"⏳ مدة العقد المقترحة: *{contract_duration}*\n"
                            f"💵 الدخول: `{entry_price}$` | الوقف (قمة الشمعة): `{stop_loss}$`\n"
                            f"🎯 الهدف: `{target}$` (RR 1.5)\n"
                            f"⚡ RVOL: `{rvol:.2f}x` | RSI: `{rsi:.1f}`"
                        )
                        send_telegram_message(msg)
                        time.sleep(1)
            except Exception as e:
                print(f"Error on {ticker}: {e}")
                continue

        # --- 3. التقرير اليومي الختامي ---
        if now_sa.hour >= 24 and not report_sent_today:
            success_str = ", ".join(successful_tickers) if successful_tickers else "لا توجد"
            failed_str = ", ".join(failed_tickers) if failed_tickers else "لا توجد"
            running_str = ", ".join([f"{t} ({i['type']})" for t, i in active_trades.items()]) if active_trades else "لا توجد"

            report_msg = (
                f"📊 *التقرير الختامي اليومي لرادار النخبة لجلسة {current_day}*\n\n"
                f"🎯 إجمالي الفرص: {signal_counter}\n"
                f"✅ الناجحة ({success_count}): {success_str}\n"
                f"🛑 الخاسرة ({failed_count}): {failed_str}\n"
                f"⏳ المستمرة: {running_str}\n"
                f"───────────────────\n"
                f"أداء احترافي ومدروس يا بطل! 🦅🔥"
            )
            send_telegram_message(report_msg)
            report_sent_today = True

        time.sleep(20)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    try:
        # إرسال صفقة التجربة فوراً دون انتظار جلب البيانات
        send_forced_test_signal()
    except Exception as e:
        print(f"Startup test signal error: {e}")
        
    analyze_market_and_send()
