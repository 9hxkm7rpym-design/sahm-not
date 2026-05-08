import yfinance as yf
import requests
import time
import pandas_ta as ta
from threading import Thread
from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home(): 
    return "Ultra-Pro-Radar-V1: Operational"

# --- الإعدادات الأساسية ---
TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = "1068286006"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try: requests.post(url, json=payload, timeout=8)
    except: pass

# --- محرك الأخبار المؤثرة ---
def get_world_news():
    try:
        # فحص أخبار السوق العام لجلب أخبار الحروب والاقتصاد
        spy = yf.Ticker("SPY")
        news_list = spy.news[:2] 
        for item in news_list:
            title = item.get('title')
            link = item.get('link')
            msg = f"🌍 <b>عاجل من الأسواق العالمية:</b>\n\n📍 {title}\n\n🔗 <a href='{link}'>التفاصيل كاملة من المصدر</a>"
            send_message(msg)
    except: pass

# --- محرك التحليل الفني والقوة ---
def analyze_market():
    # قائمة الأسهم المختارة (القيادية والطاقة)
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'OXY', 'AMD']
    
    # رسالة ترحيبية عند التشغيل لأول مرة
    send_message("💎 <b>تم تفعيل النسخة الاحترافية النهائية</b>\nالرادار الآن يراقب الأخبار والتحليلات بدقة عالية.")
    
    last_news_time = 0
    
    while True:
        current_time = time.time()
        
        # إرسال تحديث إخباري كل ساعة
        if current_time - last_news_time > 3600:
            get_world_news()
            last_news_time = current_time

        for symbol in symbols:
            try:
                data = yf.download(symbol, period='1d', interval='1m', progress=False)
                if data.empty or len(data) < 30: continue

                # حساب المؤشرات
                rsi = ta.rsi(data['Close'], length=14).iloc[-1]
                ema_fast = data['Close'].rolling(window=9).mean().iloc[-1]
                ema_slow = data['Close'].rolling(window=21).mean().iloc[-1]
                price = data['Close'].iloc[-1]

                signal = ""
                strength = ""
                score = 0

                # منطق تحليل الـ CALL
                if rsi < 40:
                    signal = "CALL 🟢"
                    if rsi < 30: score += 1
                    if price > ema_fast: score += 1
                    if ema_fast > ema_slow: score += 1
                
                # منطق تحليل الـ PUT
                elif rsi > 60:
                    signal = "PUT 🔴"
                    if rsi > 70: score += 1
                    if price < ema_fast: score += 1
                    if ema_fast < ema_slow: score += 1

                if signal:
                    # تقييم احتمال النجاح
                    if score >= 2:
                        strength = "🔥 <b>احتمال نجاح قوي جداً</b>"
                    else:
                        strength = "🟡 <b>احتمال نجاح متوسط</b>"

                    # حساب الأهداف (تقريبي)
                    target = price * 1.01 if "CALL" in signal else price * 0.99
                    stop_loss = price * 0.993 if "CALL" in signal else price * 1.007

                    msg = (
                        f"🎯 <b>صيدة جديدة: {symbol}</b>\n"
                        f"--------------------------\n"
                        f"📍 الإشارة: {signal}\n"
                        f"📊 التقييم: {strength}\n"
                        f"💰 السعر الحالي: ${price:.2f}\n"
                        f"💎 السترايك المتوقع: {round(price)}$\n"
                        f"🚀 الهدف: ${target:.2f}\n"
                        f"⚠️ وقف الخسارة: ${stop_loss:.2f}\n"
                        f"📈 RSI: {int(rsi)}\n"
                        f"--------------------------\n"
                        f"🔗 <a href='https://www.tradingview.com/chart/?symbol={symbol}'>فتح الشارت المباشر</a>"
                    )
                    send_message(msg)
                    time.sleep(3) # انتظار لتجنب الحظر
            except: pass
        
        time.sleep(30) # دورة مسح كل 30 ثانية لضمان الاستقرار

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    analyze_market()
