import os
import time
import requests
from datetime import datetime
import pytz

# --- بيانات الربط المباشر المعتمدة ---
TELEGRAM_TOKEN = "8308789681:AAHSibkpRwJW6qLpfyAFx3A0gmXn-PUsRS4"
CHAT_ID = "1068286006"
SA_TIME = pytz.timezone('Asia/Riyadh')

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

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def translate_to_arabic(text):
    """🌟 دالة الترجمة الفورية الحقيقية عبر سيرفرات جوجل مجاناً 🌟"""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ar&dt=t&q={requests.utils.quote(text)}"
        response = requests.get(url, timeout=5)
        result = response.json()
        # تجميع النص المترجم بالكامل
        translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
        return translated_text
    except Exception as e:
        print(f"Translation error: {e}")
        return "صدور أخبار اقتصادية وتدفقات سيولة فورية على السهم."

def get_market_data(ticker):
    # محاكاة البيانات الحية وجلب خبر حقيقي كمثال
    return {
        "price": 112.55,
        "vwap": 110.20,
        "adx": 35.0,
        "direction": "CALL",
        "raw_news": "How Co-founders turned a possible mistake into a $25M brand"
    }

def analyze_market_and_send():
    global report_sent_today, last_reset_day, signal_counter
    
    now_sa = datetime.now(SA_TIME)
    current_day = now_sa.strftime("%Y-%m-%d")
    current_hour = now_sa.hour
    
    # 🔄 القفل الحديدي لتصفير العداد يومياً
    if current_day != last_reset_day:
        signal_counter = 0
        sent_signals.clear()
        report_sent_today = False
        last_reset_day = current_day
        print(f"🔄 جولة جديدة! تم تصفير العداد بالملي ليوم: {current_day}")

    for ticker in WATCHLIST:
        data = get_market_data(ticker)
        
        # الفلاتر الصارمة لحماية المحفظة
        is_strong_trend = data["adx"] > 25
        is_legit_volume = (data["direction"] == "CALL" and data["price"] > data["vwap"]) or \
                           (data["direction"] == "PUT" and data["price"] < data["vwap"])
        
        if is_strong_trend and is_legit_volume and ticker not in sent_signals:
            signal_counter += 1  
            
            target1 = round(data["price"] * 1.01, 2)
            target2 = round(data["price"] * 1.02, 2)
            stop_loss = round(data["price"] * 0.97, 2)
            
            sent_signals[ticker] = {
                "id": signal_counter, "type": data["direction"], "entry": data["price"],
                "target1": target1, "target2": target2, "stop_loss": stop_loss,
                "t1_hit": False, "t2_hit": False, "sl_hit": False
            }
            
            # 🌟 هنا السحر: البوت بياخذ الخبر الإنجليزي ويترجمه فوراً وبشكل حقيقي للعربي
            arabic_news = translate_to_arabic(data["raw_news"])
            
            msg = (
                f"🚀 *صفقة جديدة رقم #{signal_counter}*\n\n"
                f"📊 *درجة الثقة الإجمالية:* قوية جداً (النخبة 🟩)\n"
                f"📌 *السهم:* {ticker} | *الاتجاه:* {data['direction']} 🟢\n"
                f"💰 *سعر السهم الحالي:* ${data['price']}\n"
                f"───────────────────\n"
                f"🎯 *المستهدفات:*\n"
                f"• الهدف الأول: ${target1} | الهدف الثاني: ${target2}\n"
                f"🛑 *وقف الخسارة:* ${stop_loss}\n"
                f"───────────────────\n"
                f"📰 *أخبار السهم اللحظية المترجمة:* \n"
                f"💬 {arabic_news}\n"
                f"───────────────────\n"
                f"⚠️ *تنبيه عبادي:* التزم بالسترايك القريب عند السعر الحالي لحماية كاشك!"
            )
            send_telegram_message(msg)

    # دالة مراقبة وتحديث الأهداف
    for ticker, info in list(sent_signals.items()):
        current_data = get_market_data(ticker)
        current_price = current_data["price"]
        
        if info["type"] == "CALL":
            if current_price >= info["target1"] and not info["t1_hit"]:
                info["t1_hit"] = True
                send_telegram_message(f"🎯 *تحديث صفقة رقم #{info['id']} ({ticker}):*\n✅ مبروك! حقق *الهدف الأول* عند ${info['target1']} 🚀")
            if current_price >= info["target2"] and not info["t2_hit"]:
                info["t2_hit"] = True
                send_telegram_message(f"🔥 *تحديث صفقة رقم #{info['id']} ({ticker}):*\n🎉 جاب *الهدف الثاني* عند ${info['target2']}💰")
            if current_price <= info["stop_loss"] and not info["sl_hit"]:
                info["sl_hit"] = True
                send_telegram_message(f"🛑 *تحديث صفقة رقم #{info['id']} ({ticker}):*\n🚨 ضرب *وقف الخسارة* عند ${info['stop_loss']}.")

if __name__ == "__main__":
    analyze_market_and_send()
