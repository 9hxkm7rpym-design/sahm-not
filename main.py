import yfinance as yf
import requests
import time
import pandas_ta as ta

TOKEN = "8308789681:AAFLJuVqqQ3Jqtgth51in4IZpN1X_1aZYAE"
CHAT_ID = 1068286006
stocks = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'META', 'GOOGL', 'AMD', 'NFLX', 'SMCI', 'COIN']

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

print("🚀 البوت انطلق...")
send_msg("🛡️ **تم تفعيل المحلل الخبير على السيرفر!**\nأنا الآن أراقب لك السوق 24 ساعة (أهداف، سترايكات، ومخاطر).")

while True:
    for ticker in stocks:
        try:
            df = yf.download(ticker, period="5d", interval="15m", progress=False)
            if df.empty: continue
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            price = df['Close'].iloc[-1]
            rsi = ta.rsi(df['Close'], length=14).iloc[-1]
            bb = ta.bbands(df['Close'], length=20, std=2)
            lower_b = bb['BBL_20_2.0'].iloc[-1]
            
            if rsi <= 32 and price <= (lower_b * 1.002):
                t1, t2, sl = price * 1.02, price * 1.05, price * 0.975
                msg = (f"🔥 **توصية دخول (CALL)**\n💹 السهم: #{ticker}\n💵 السعر: {price:.2f}\n🎯 أهداف: {t1:.2f} - {t2:.2f}\n🛑 الوقف: {sl:.2f}")
                send_msg(msg)
        except: continue
    time.sleep(300)
