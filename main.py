import telebot
import requests
import time
import pandas as pd
import pandas_ta as ta
from flask import Flask
from threading import Thread
import os

# --- إعدادات سلطان (نسخة القناص الصارم + منع التعارض) ---
TOKEN = '8308789681:AAHYYl6et5Ef7h8s8A4D7IKPm-vczx6SvIo'
CHAT_ID = '1068286006'
bot = telebot.TeleBot(TOKEN)

user_active_trades = {}
app = Flask('')

@app.route('/')
def home(): return "رادار سلطان: نسخة القناص الصارم (80% ثقة) تعمل! 🦅"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# قائمة الشركات المنقحة (تذبذب عالي + حلال)
WATCHLIST = ['AAPL', 'NVDA', 'TSLA', 'AMZN', 'AMD', 'LCID', 'NIO', 'RIVN', 'BABA', 'OXY', 'CVX', 'RBLX']

@bot.message_handler(commands=['trade'])
def start_manual_trade(message):
    try:
        symbol = message.text.split()[1].upper()
        user_active_trades[symbol] = {'status': 'monitoring', 'notified_h1': False}
        bot.reply_to(message, f"✅ تم تفعيل رادار المتابعة لـ {symbol}. الله يبارك لك في رزقك.")
    except:
        bot.reply_to(message, "⚠️ أرسل كذا: /trade NVDA")

@bot.message_handler(commands=['close'])
def stop_manual_trade(message):
    try:
        symbol = message.text.split()[1].upper()
        if symbol in user_active_trades:
            del user_active_trades[symbol]
            bot.reply_to(message, f"📴 تم إيقاف متابعة {symbol}.")
    except:
        bot.reply_to(message, "⚠️ أرسل كذا: /close NVDA")

def get_market_opportunities():
    while True:
        for t in WATCHLIST:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=15m&range=5d"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                data = r['chart']['result'][0]['indicators']['quote'][0]
                df = pd.DataFrame(data).ffill()
                
                p = round(df['close'].iloc[-1], 2)
                res = round(df['high'].tail(30).max(), 2)
                sup = round(df['low'].tail(30).min(), 2)
                
                df['macd_h'] = ta.macd(df['close'])['MACDh_12_26_9']
                vol_ratio = round(df['volume'].iloc[-1] / df['volume'].tail(20).mean(), 1)
                
                status = None
                scenario = ""
                score = 50 # نبدأ بـ 50%
                
                # --- فلتر الصرامة ---
                if p >= res * 0.998 and df['macd_h'].iloc[-1] < df['macd_h'].iloc[-2]:
                    status = "PUT 🔴"
                    scenario = f"⚠️ **فخ صعودي:** السهم يضرب مقاومة ({res}) والزخم يضعف."
                    if vol_ratio > 1.5: score += 35 # زيادة ثقة للسيولة العالية
                elif p <= sup * 1.002 and df['macd_h'].iloc[-1] > df['macd_h'].iloc[-2]:
                    status = "CALL 🟢"
                    scenario = f"✅ **منطقة طلب:** السهم يرتد من دعم ({sup}) بسيولة هوامير."
                    if vol_ratio > 1.5: score += 35

                # لا يرسل إلا إذا الثقة 80% أو أكثر
                if status and score >= 80:
                    strike = int(round(p))
                    msg = (f"🦅 **قناص سلطان (ثقة 85%+): {t}**\n"
                           f"----------------------------------\n"
                           f"🎬 **السيناريو:** {scenario}\n"
                           f"🎯 **الثقة:** انفجارية 🔥 ({score}%)\n"
                           f"----------------------------------\n"
                           f"📈 الاتجاه: {status} | السعر: `${p}`\n"
                           f"📋 Strike المقترح: **{strike}**\n"
                           f"----------------------------------\n"
                           f"💡 أرسل `/trade {t}` للمتابعة اللحظية.")
                    bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                    time.sleep(2)
            except: pass
        time.sleep(300)

def monitor_active_trades():
    while True:
        for t in list(user_active_trades.keys()):
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1m&range=1d"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
                res_data = r['chart']['result'][0]
                p = round(res_data['meta']['regularMarketPrice'], 2)
                h_max = res_data['indicators']['quote'][0]['high'][-10:]
                target_1 = round(max(h_max), 2)
                
                if p >= target_1 and not user_active_trades[t]['notified_h1']:
                    df_v = pd.DataFrame(res_data['indicators']['quote'][0]).ffill()
                    vol_r = df_v['volume'].iloc[-1] / df_v['volume'].tail(10).mean()
                    advice = "🚀 كمل للهدف الثاني!" if vol_r > 1.4 else "⚠️ اكتفِ بالربح."
                    bot.send_message(CHAT_ID, f"🎯 **هدف تحقق في {t} (${p})**\n🧐 **المحلل:** {advice}")
                    user_active_trades[t]['notified_h1'] = True
            except: pass
        time.sleep(30)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=get_market_opportunities).start()
    Thread(target=monitor_active_trades).start()
    # أهم سطر لمنع التعارض 409
    while True:
        try:
            bot.polling(none_stop=True, interval=3, timeout=20)
        except Exception as e:
            time.sleep(5)
