import os
import time
import requests
from datetime import datetime

# --- الإعدادات الأساسية (توكن البوت والـ Chat ID) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

# --- قائمة الـ 29 سهم المعتمدة (القديمة + XOM الحلال) ---
WATCHLIST = [
    "NVDA", "TSLA", "MSFT", "AMZN", "AAPL", "META", "OXY", "NFLX", "AMD", "GOOGL",
    "BA", "BABA", "COIN", "DIS", "JPM", "MARA", "NIO", "ORCL", "PLTR", "QQQ",
    "ROKU", "SPY", "SQ", "UBER", "V", "WMT", "XOM", "PFE", "SOFI"
]

# --- الذاكرة المؤقتة لمنع التكرار (State Management) ---
sent_signals = {}      # لحفظ الصفقات النشطة لمنع التكرار
report_sent_today = False
last_report_date = ""

def send_telegram_message(text):
    """إرسال الرسائل إلى التليجرام تلقائياً"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")

def translate_and_summarize_news(raw_news_text):
    """تلخيص وترجمة زبدة الأخبار فورياً إلى العربية"""
    if "inventory" in raw_news_text.lower() or "oil" in raw_news_text.lower():
        return "تحديث مخزونات الطاقة والنفط الأمريكية المؤثرة على الحركة."
    elif "earnings" in raw_news_text.lower() or "revenue" in raw_news_text.lower():
        return "إعلان النتائج المالية الربع سنوية للشركة الحين."
    return "صدور أخبار اقتصادية وتدفقات سيولة فورية على السهم."

def analyze_market_and_send():
    global report_sent_today, last_report_date
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_hour = datetime.now().hour
    
    # تصفير عداد التقرير اليومي مع بداية يوم جديد
    if current_date != last_report_date:
        report_sent_today = False
        last_report_date = current_date

    # --- 1. فحص وتحليل الأسهم أثناء الجلسة (إرسال الصفقات) ---
    signal_counter = len(sent_signals) + 1
    
    for ticker in WATCHLIST:
        has_setup = False # (هنا يوضع شرط الاستراتيجية المدمجة الخاص بك)
        
        if has_setup and ticker not in sent_signals:
            entry_price = 150.0 if ticker == "XOM" else 100.0  # مثال لايف من الشارت
            target_1 = entry_price * 1.02
            stop_loss = entry_price * 0.99
            
            # صياغة الرسالة بـ "خلطة المعلم" المعتمدة (ترقيم وتحديد قوة)
            msg = (
                f"🚨 *صفقة رقم #{signal_counter}*\n"
                f"▪️ *السهم:* {ticker} 🌙\n"
                f"▪️ *نوع العقد المتوقع:* CALL (صعود)\n"
                f"▪️ *مدرسة الدخول:* مناطق الهوامير (SMC) + فوليوم عالي\n"
                f"▪️ *درجة القوة:* قوي 🟩\n"
                f"▪️ *سعر دخول السهم الحالي:* ${entry_price:.2f}\n"
                f"🎯 *الهدف الحقيقي (عظم الشارت):* ${target_1:.2f}\n"
                f"🛑 *وقف الخسارة بالملي:* ${stop_loss:.2f}\n"
                f"--- \n"
                f"⚠️ *ملاحظة المخاطرة:* نسبة المخاطرة ممتازة (الهدف ضعف الوقف)."
            )
            
            send_telegram_message(msg)
            sent_signals[ticker] = {"signal_id": signal_counter, "status": "Active"}
            
        # --- 2. إرسال الأخبار الفورية المترجمة بالعربي مع السهم ---
        has_urgent_news = False # يتم ربطه بـ API الأخبار لديك
        if has_urgent_news:
            raw_news = "Urgent market updates and institutional volume spike."
            arabic_news = translate_and_summarize_news(raw_news)
            news_msg = (
                f"📰 *خبر عاجل وفوري - سهم {ticker}*\n"
                f"▪️ *الخبر بالعربي:* {arabic_news}\n"
                f"▪️ *تأثيره المتوقع:* يدعم عزم الحركة الحالية على الشارت."
            )
            send_telegram_message(news_msg)

    # --- 3. قفل التقرير اليومي: يرسل مرة واحدة فقط بعد إغلاق السوق ---
    if current_hour >= 23 and not report_sent_today:
        report_msg = (
            f"📊 *التقرير الختامي اليومي لجلسة {current_date}*\n"
            f"تم مراقبة الـ 29 سهم كاملة اليوم مية بالمية.\n"
            f"▪️ عدد الفرص الكلية المرسلة: {len(sent_signals)}\n"
            f"حالة محفظتك وتداولاتك في سهم في أمان، نلقاكم الجلسة القادمة بروقان!"
        )
        send_telegram_message(report_msg)
        report_sent_today = True # قفل الإرسال نهائياً لمنع التكرار ألف مرة

if __name__ == "__main__":
    # 🌟 إرسال رسالة التحية الفورية تلقائياً بمجرد تشغيل السيرفر بدون تدخل منك:
    try:
        # قراءة ملف مؤقت للتأكد أن التحية ترسل أول مرة فقط ولا تتكرر مع الـ Cron-job
        if not os.path.exists("booted.txt"):
            startup_msg = (
                "🚀 *أبشرك يا عبادي.. وحش \"خلطة المعلم\" اشتغل الحين تلقائياً!*\n"
                "🎯 الـ 29 سهم تحت المجهر بالملي، والسيستم جاهز لافتتاح السوق وبداية جلب الغنايم بروقان وبدون أي تكرار مزعج!"
            )
            send_telegram_message(startup_msg)
            # إنشاء ملف صغير ليحفظ حالة التشغيل
            with open("booted.txt", "w") as f:
                f.write("true")
    except Exception as e:
        print(f"Startup greeting error: {e}")
        
    # تشغيل الفحص والتحليل الأساسي للسوق تلقائياً
    analyze_market_and_send()
