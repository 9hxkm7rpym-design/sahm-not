import os
import time
import threading
from datetime import datetime, time as dtime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

TELEGRAM_TOKEN = "8472180858:AAG2eMBTuzRMz-tLkT2MV9ow_YjeUbXAbyY"
CHAT_ID = "1068286006"

WATCHLIST = [
    "NVDA", "TSLA", "MSFT", "AMZN", "AAPL", "META", "OXY", "NFLX", "AMD", "GOOGL",
    "BA", "BABA", "COIN", "DIS", "JPM", "MARA", "NIO", "ORCL", "PLTR", "QQQ",
    "ROKU", "SPY", "XYZ", "UBER", "V", "WMT", "XOM", "PFE", "SOFI"
]

active_trades = {}
last_signaled_price = {}
signal_count = 0
stats = {"wins": 0, "losses": 0}
grade_counts = {"elite": 0, "strong": 0, "good": 0}
eod_reported_date = ""
active_trading_date = ""
last_heartbeat_ts = 0.0

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot Running".encode("utf-8"))

    def log_message(self, format, *args):
        return


def run_health_server():
    while True:
        try:
            port = int(os.environ.get("PORT", 8080))
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            server.serve_forever()
        except Exception as e:
            print(f"Health server error: {e}")
            time.sleep(3)


def send_tg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    try:
        res = SESSION.post(url, json=payload, timeout=6)
        if res.status_code != 200:
            print(f"TG Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"TG Exception: {e}")


def ksa_now():
    return datetime.now(timezone(timedelta(hours=3)))


def is_us_winter_open(now_ksa):
    if now_ksa.weekday() >= 5:
        return False
    t = now_ksa.time()
    return dtime(17, 30) <= t <= dtime(23, 59)


def fetch_quote_and_analysis(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=5d"
    try:
        r = SESSION.get(url, timeout=6)
        if r.status_code != 200:
            return None
        data = r.json()
        chart = data.get("chart") or {}
        results = chart.get("result") or []
        if not results:
            return None

        result0 = results[0] or {}
        meta = result0.get("meta") or {}
        indicators = result0.get("indicators") or {}
        quotes = indicators.get("quote") or []
        if not quotes:
            return None

        quote = quotes[0] or {}
        price = meta.get("regularMarketPrice")
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        if not price or not prev_close:
            return None

        closes = [c for c in (quote.get("close") or []) if c is not None]
        lows = [l for l in (quote.get("low") or []) if l is not None]
        highs = [h for h in (quote.get("high") or []) if h is not None]
        volumes = [v for v in (quote.get("volume") or []) if v is not None]

        if len(closes) < 4:
            return None

        pct = ((price - prev_close) / prev_close) * 100
        ma_fast = sum(closes[-5:]) / min(len(closes), 5)
        ma_slow = sum(closes[-15:]) / min(len(closes), 15)

        recent_3_change_pct = ((closes[-1] - closes[-3]) / closes[-3]) * 100 if closes[-3] > 0 else 0.0
        vs_ma5_pct = ((price - ma_fast) / ma_fast) * 100 if ma_fast > 0 else 0.0

        avg_vol = (sum(volumes[:-1]) / max(1, len(volumes) - 1)) if len(volumes) > 1 else 0
        last_vol = volumes[-1] if volumes else 0
        vol_ratio = round((last_vol / avg_vol), 2) if avg_vol > 0 else 1.0

        swing_low = min(lows[-10:]) if lows else price * 0.99
        swing_high = max(highs[-10:]) if highs else price * 1.01

        ranges = [h - l for h, l in zip(highs[-15:], lows[-15:]) if h is not None and l is not None]
        avg_5m_move = max(sum(ranges) / len(ranges), price * 0.0015) if ranges else price * 0.002

        return {
            "price": round(float(price), 2),
            "pct": round(float(pct), 2),
            "ma_fast": round(float(ma_fast), 2),
            "ma_slow": round(float(ma_slow), 2),
            "recent_3_pct": round(float(recent_3_change_pct), 2),
            "vs_ma5_pct": round(float(vs_ma5_pct), 2),
            "vol_ratio": vol_ratio,
            "swing_low": round(float(swing_low), 2),
            "swing_high": round(float(swing_high), 2),
            "avg_5m_move": float(avg_5m_move)
        }
    except Exception as e:
        print(f"Analysis error {ticker}: {e}")
        return None


def score_and_grade(side, price, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct):
    score = 0
    abs_pct = abs(pct)

    if abs_pct >= 2.0:
        score += 30
    elif abs_pct >= 1.0:
        score += 22
    elif abs_pct >= 0.4:
        score += 15
    else:
        score += 8

    if side == "CALL":
        if price >= ma_fast and ma_fast >= ma_slow:
            score += 30
        elif price >= ma_fast * 0.997 and ma_fast >= ma_slow * 0.995:
            score += 20
        else:
            score += 10
    else:
        if price <= ma_fast and ma_fast <= ma_slow:
            score += 30
        elif price <= ma_fast * 1.003 and ma_fast <= ma_slow * 1.005:
            score += 20
        else:
            score += 10

    if vol_ratio >= 1.2:
        score += 20
    elif vol_ratio >= 0.7:
        score += 15
    elif vol_ratio >= 0.3:
        score += 10
    else:
        score += 5

    if side == "CALL":
        if recent_3_pct >= 0.15:
            score += 20
        elif recent_3_pct >= 0.0:
            score += 12
        else:
            score += 5
    else:
        if recent_3_pct <= -0.15:
            score += 20
        elif recent_3_pct <= 0.0:
            score += 12
        else:
            score += 5

    score = min(100, score)

    if score >= 75:
        return "elite", "⭐ نخبة", score, "دخول أساسي (أعلى قوة)"
    elif score >= 50:
        return "strong", "🔥 ممتازة", score, "دخول متوسط متوازن"
    else:
        return "good", "⚡ جيدة", score, "دخول خفيف / متابعة"


def format_target_eta(current_price, target_price, avg_5m_move):
    dist = abs(target_price - current_price)
    bars_needed = max(1.0, dist / max(avg_5m_move, 0.01))
    est_mins = max(5, int(round(bars_needed * 5 * 1.25)))

    if est_mins < 60:
        return f"~{est_mins} دقيقة"
    elif est_mins < 390:
        hours = round(est_mins / 60, 1)
        return f"~{hours} ساعة"
    else:
        trading_days = max(1.0, round(est_mins / 390, 1))
        if trading_days <= 1.2:
            return "~1 يوم تداول"
        return f"~{trading_days} أيام تداول"


def can_signal_again(ticker, current_price):
    prev = last_signaled_price.get(ticker)
    if prev is None or prev <= 0:
        return True
    move_pct = abs(current_price - prev) / prev * 100
    return move_pct >= 0.12


def reset_daily_counters(date_str):
    global signal_count, stats, grade_counts, active_trading_date
    signal_count = 0
    stats = {"wins": 0, "losses": 0}
    grade_counts = {"elite": 0, "strong": 0, "good": 0}
    active_trading_date = date_str


def send_end_of_day_report(date_str, now_ksa):
    global eod_reported_date
    open_count = len(active_trades)
    decided = stats["wins"] + stats["losses"]
    win_rate = round((stats["wins"] / decided) * 100, 1) if decided > 0 else 0.0

    msg = (
        f"📊 تقرير نهاية اليوم ({date_str})\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📌 صفقات اليوم: {signal_count}\n"
        f"🏅 الدرجات: ⭐ نخبة ({grade_counts['elite']}) | 🔥 ممتازة ({grade_counts['strong']}) | ⚡ جيدة ({grade_counts['good']})\n"
        f"✅ أهداف محققة اليوم: {stats['wins']}\n"
        f"❌ ضربت الوقف اليوم: {stats['losses']}\n"
        f"⏳ لا تزال متابعة للهدف/الوقف: {open_count}\n"
        f"🎯 نسبة النجاح المحسومة: {win_rate}%\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⏰ الساعة: {now_ksa.strftime('%H:%M')} KSA"
    )
    send_tg(msg)
    eod_reported_date = date_str


def monitor_active_trades():
    done = []
    for trade_key, tr in list(active_trades.items()):
        try:
            ticker = tr["ticker"]
            q = fetch_quote_and_analysis(ticker)
            if not q:
                continue
            p = q["price"]
            num = tr["num"]

            if tr["side"] == "CALL":
                if not tr["t1_hit"] and p >= tr["t1"]:
                    tr["t1_hit"] = True
                    stats["wins"] += 1
                    send_tg(f"✅ رقم {num} — {ticker} حقق الهدف 1 (${p})")
                if p >= tr["t2"]:
                    if not tr["t1_hit"]:
                        stats["wins"] += 1
                    stats["wins"] += 1
                    send_tg(f"✅ رقم {num} — {ticker} حقق الهدف 2 (${p})")
                    done.append(trade_key)
                elif p <= tr["sl"]:
                    stats["losses"] += 1
                    send_tg(f"❌ رقم {num} — {ticker} ضرب الوقف (${p})")
                    done.append(trade_key)
            else:
                if not tr["t1_hit"] and p <= tr["t1"]:
                    tr["t1_hit"] = True
                    stats["wins"] += 1
                    send_tg(f"✅ رقم {num} — {ticker} حقق الهدف 1 (${p})")
                if p <= tr["t2"]:
                    if not tr["t1_hit"]:
                        stats["wins"] += 1
                    stats["wins"] += 1
                    send_tg(f"✅ رقم {num} — {ticker} حقق الهدف 2 (${p})")
                    done.append(trade_key)
                elif p >= tr["sl"]:
                    stats["losses"] += 1
                    send_tg(f"❌ رقم {num} — {ticker} ضرب الوقف (${p})")
                    done.append(trade_key)
        except Exception as e:
            print(f"Monitor error {trade_key}: {e}")

    for k in done:
        active_trades.pop(k, None)


def scan_new_setups():
    global signal_count, last_heartbeat_ts
    ok_count = 0
    missing = []
    top_move = ("-", 0.0)

    for ticker in WATCHLIST:
        try:
            q = fetch_quote_and_analysis(ticker)
            time.sleep(0.05)
            if not q:
                missing.append(ticker)
                continue
            ok_count += 1

            p = q["price"]
            pct = q["pct"]
            if abs(pct) > abs(top_move[1]):
                top_move = (ticker, pct)

            if not can_signal_again(ticker, p):
                continue

            ma_fast = q["ma_fast"]
            ma_slow = q["ma_slow"]
            vol_ratio = q["vol_ratio"]
            recent_3_pct = q["recent_3_pct"]
            vs_ma5_pct = q["vs_ma5_pct"]
            step_move = max(q["avg_5m_move"], p * 0.0025)

            bullish_setup = (vol_ratio >= 0.05) and (recent_3_pct >= 0.08 or vs_ma5_pct >= 0.12)
            bearish_setup = (vol_ratio >= 0.05) and (recent_3_pct <= -0.08 or vs_ma5_pct <= -0.12)

            if bullish_setup:
                signal_count += 1
                trade_key = f"{ticker}_{signal_count}"
                grade_key, grade_label, score, sizing_hint = score_and_grade(
                    "CALL", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct
                )
                grade_counts[grade_key] += 1

                entry_low = round(min(p, ma_fast) * 0.999, 2)
                entry_high = round(max(p, ma_fast) * 1.001, 2)
                t1 = round(max(p * 1.008, p + step_move * 1.5), 2)
                t2 = round(max(p * 1.015, p + step_move * 3.0), 2)
                sl = round(min(q["swing_low"], p - step_move * 2.0), 2)

                eta_t1 = format_target_eta(p, t1, q["avg_5m_move"])
                eta_t2 = format_target_eta(p, t2, q["avg_5m_move"])

                active_trades[trade_key] = {
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "CALL",
                    "t1": t1,
                    "t2": t2,
                    "sl": sl,
                    "t1_hit": False
                }
                last_signaled_price[ticker] = p

                prefix = "🚨 فرصة نخبة!\n" if grade_key == "elite" else ""
                msg = (
                    f"{prefix}🟢 صفقة #{signal_count} — {ticker} (CALL) | {grade_label} ({score}/100)\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🏅 الدرجة: {grade_label} — {sizing_hint}\n"
                    f"💵 السعر الحالي: ${p} (pct: {pct:+.2f}%)\n"
                    f"📍 منطقة الدخول: ${entry_low} — ${entry_high}\n"
                    f"🎯 الهدف 1: ${t1} — المتوقع: {eta_t1}\n"
                    f"🎯 الهدف 2: ${t2} — المتوقع: {eta_t2}\n"
                    f"🛑 الوقف الفني: ${sl}\n"
                    f"📊 التحليل: pct {pct:+.2f}% | 3 شمعات {recent_3_pct:+.2f}% | MA5 ${ma_fast}/MA15 ${ma_slow} | حجم {vol_ratio}x"
                )
                send_tg(msg)
                time.sleep(0.25)

            elif bearish_setup:
                signal_count += 1
                trade_key = f"{ticker}_{signal_count}"
                grade_key, grade_label, score, sizing_hint = score_and_grade(
                    "PUT", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct
                )
                grade_counts[grade_key] += 1

                entry_low = round(min(p, ma_fast) * 0.999, 2)
                entry_high = round(max(p, ma_fast) * 1.001, 2)
                t1 = round(min(p * 0.992, p - step_move * 1.5), 2)
                t2 = round(min(p * 0.985, p - step_move * 3.0), 2)
                sl = round(max(q["swing_high"], p + step_move * 2.0), 2)

                eta_t1 = format_target_eta(p, t1, q["avg_5m_move"])
                eta_t2 = format_target_eta(p, t2, q["avg_5m_move"])

                active_trades[trade_key] = {
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "PUT",
                    "t1": t1,
                    "t2": t2,
                    "sl": sl,
                    "t1_hit": False
                }
                last_signaled_price[ticker] = p

                prefix = "🚨 فرصة نخبة!\n" if grade_key == "elite" else ""
                msg = (
                    f"{prefix}🔴 صفقة #{signal_count} — {ticker} (PUT) | {grade_label} ({score}/100)\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🏅 الدرجة: {grade_label} — {sizing_hint}\n"
                    f"💵 السعر الحالي: ${p} (pct: {pct:+.2f}%)\n"
                    f"📍 منطقة الدخول: ${entry_low} — ${entry_high}\n"
                    f"🎯 الهدف 1: ${t1} — المتوقع: {eta_t1}\n"
                    f"🎯 الهدف 2: ${t2} — المتوقع: {eta_t2}\n"
                    f"🛑 الوقف الفني: ${sl}\n"
                    f"📊 التحليل: pct {pct:+.2f}% | 3 شمعات {recent_3_pct:+.2f}% | MA5 ${ma_fast}/MA15 ${ma_slow} | حجم {vol_ratio}x"
                )
                send_tg(msg)
                time.sleep(0.25)
        except Exception as e:
            print(f"Scan error {ticker}: {e}")

    now_ts = time.time()
    if now_ts - last_heartbeat_ts >= 300:
        last_heartbeat_ts = now_ts
        miss_txt = f" | ناقص: {','.join(missing)}" if missing else ""
        send_tg(
            f"📡 نبضة فحص: قراءة {ok_count}/{len(WATCHLIST)} سهم{miss_txt} | أعلى حركة: {top_move[0]} ({top_move[1]:+.2f}%) | صفقات اليوم: {signal_count}"
        )


def main_loop():
    while True:
        try:
            now_ksa = ksa_now()
            today_str = now_ksa.strftime("%Y-%m-%d")

            if is_us_winter_open(now_ksa):
                if active_trading_date != today_str:
                    reset_daily_counters(today_str)
                monitor_active_trades()
                scan_new_setups()
                time.sleep(10)
            else:
                if (
                    now_ksa.weekday() < 5
                    and active_trading_date == today_str
                    and eod_reported_date != today_str
                    and now_ksa.time() >= dtime(0, 1)
                    and now_ksa.time() <= dtime(4, 0)
                ):
                    send_end_of_day_report(today_str, now_ksa)
                time.sleep(45)
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    send_tg("⚡ تم تشغيل البوت بنسخة الصفقات المتدفقة (بدون تقييد pct).")
    main_loop()
