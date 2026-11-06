import time
import requests
import yfinance as yf
from datetime import datetime

# ==================== إعدادات تليجرام ====================
TELEGRAM_BOT_TOKEN = "ضع_التوكن_هنا"
TELEGRAM_CHAT_ID = "ضع_الروم_اي دي_هنا"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"خطأ في إرسال رسالة تليجرام: {e}")

# ==================== قائمة الأسهم المراقبة (Watchlist) ====================
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC",
    "PLTR", "BA", "DIS", "PYPL", "SQ", "COIN", "MARA", "RIVN", "NIO", "SNAP",
    "UBER", "ROKU", "SHOP", "BABA", "XOM", "JPM", "BAC", "PFE", "SPY"
]

def check_market_momentum():
    print("🚀 جاري فحص السوق والأسهم بناءً على محرك الزخم الحقيقي ونطاقات الدخول الذكية...")
    
    for symbol in WATCHLIST:
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period="2d", interval="1h")
            
            if df.empty or len(df) < 2:
                continue
                
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            price_change = ((current_price - prev_close) / prev_close) * 100
            
            current_volume = df['Volume'].iloc[-1]
            avg_volume = df['Volume'].mean()

            # شرط الزخم المزدوج العادل (تغير مئوي + حجم تداول نشط)
            if price_change >= 1.5 and current_volume > (avg_volume * 0.8):
                
                # حساب منطقة الدخول الذكية والأهداف وهامش الأمان
                entry_low = round(current_price * 0.998, 2)
                entry_high = round(current_price * 1.002, 2)
                target_1 = round(current_price * 1.02, 2)
                target_2 = round(current_price * 1.04, 2)
                stop_loss = round(current_price * 0.985, 2)
                
                direction = "CALL 🟢" if price_change > 0 else "PUT 🔴"
                
                # صياغة رسالة تليجرام الواضحة والمرتبة
                message = (
                    f"🔔 *تنبيه صفقة أوبشن جديدة* 🚀\n\n"
                    f"📌 *الرمز (Ticker):* `{symbol}`\n"
                    f"📈 *نوع الصفقة:* `{direction}`\n"
                    f"💵 *السعر الحالي:* `${current_price:.2f}`\n\n"
                    f"🎯 *منطقة الدخول الآمنة (Entry Zone):*\n"
                    f"`${entry_low} - ${entry_high}` *(ادخل بهذا النطاق)*\n\n"
                    f"📊 *الأهداف ووقف الخسارة:*\n"
                    f"• *الهدف الأول:* `${target_1}` 🟢\n"
                    f"• *الهدف الثاني:* `${target_2}` 🎯\n"
                    f"• *وقف الخسارة:* `${stop_loss}` 🛑\n\n"
                    f"⚡ *نسبة التغير اللحظي:* `+{price_change:.2f}%`"
                )
                
                send_telegram_message(message)
                print(f"تم إرسال تنبيه للصفقة: {symbol}")
                
        except Exception as e:
            print(f"خطأ أثناء معالجة السهم {symbol}: {e}")

if __name__ == "__main__":
    print("🤖 البوت يعمل الآن في الخلفية...")
    while True:
        # فحص السوق كل 5 دقائق
        check_market_momentum()
        time.sleep(300)
