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
daily_trades_log = []
signaled_today = set()
signal_count = 0
stats = {"wins": 0, "losses": 0}
grade_counts = {"elite": 0, "strong": 0, "good": 0}
eod_reported_date = ""
active_trading_date = ""
last_heartbeat_ts = 0.0
tg_blocked_until = 0.0

MAX_HOLD_MINUTES = 90
MIN_VOL_RATIO = 1.0  # شرط السيولة في كل الدرجات

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
    global tg_blocked_until
    now_ts = time.time()
    if now_ts < tg_blocked_until:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    try:
        res = SESSION.post(url, json=payload, timeout=6)
        if res.status_code == 429:
            retry_after = 15
            try:
                data = res.json()
                params = data.get("parameters") or {}
                retry_after = int(params.get("retry_after", 15))
            except Exception:
                pass
            tg_blocked_until = time.time() + max(5, retry_after) + 2
            print(f"TG 429 cooldown for {retry_after + 2}s")
        elif res.status_code != 200:
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

        if len(closes) < 4 or len(highs) < 4 or len(lows) < 4:
            return None

        pct = ((price - prev_close) / prev_close) * 100
        ma_fast = sum(closes[-5:]) / min(len(closes), 5)
        ma_slow = sum(closes[-15:]) / min(len(closes), 15)

        ref_3 = closes[-3] if len(closes) >= 3 else closes[0]
        recent_3_change_pct = ((closes[-1] - ref_3) / ref_3) * 100 if ref_3 > 0 else 0.0
        vs_ma5_pct = ((price - ma_fast) / ma_fast) * 100 if ma_fast > 0 else 0.0
        vs_ma15_pct = ((price - ma_slow) / ma_slow) * 100 if ma_slow > 0 else 0.0

        valid_vols = [v for v in volumes[:-1] if v is not None and v > 0]
        avg_vol = (sum(valid_vols) / len(valid_vols)) if valid_vols else 0
        last_vol = volumes[-1] if (volumes and volumes[-1] is not None) else 0
        vol_ratio = round((last_vol / avg_vol), 2) if (avg_vol > 0 and last_vol > 0) else 0.0

        short_high = max(highs[-6:])
        short_low = min(lows[-6:])
        chart_high = max(highs[-20:])
        chart_low = min(lows[-20:])

        ranges = [h - l for h, l in zip(highs[-15:], lows[-15:]) if h is not None and l is not None and h > l]
        avg_5m_move = max(sum(ranges) / len(ranges), price * 0.002) if ranges else price * 0.0025

        return {
            "price": round(float(price), 2),
            "pct": round(float(pct), 2),
            "ma_fast": round(float(ma_fast), 2),
            "ma_slow": round(float(ma_slow), 2),
            "recent_3_pct": round(float(recent_3_change_pct), 2),
            "vs_ma5_pct": round(float(vs_ma5_pct), 2),
            "vs_ma15_pct": round(float(vs_ma15_pct), 2),
            "vol_ratio": vol_ratio,
            "short_high": round(float(short_high), 2),
            "short_low": round(float(short_low), 2),
            "chart_high": round(float(chart_high), 2),
            "chart_low": round(float(chart_low), 2),
            "avg_5m_move": float(avg_5m_move)
        }
    except Exception as e:
        print(f"Analysis error {ticker}: {e}")
        return None


def compute_chart_levels(side, q):
    p = q["price"]
    step = q["avg_5m_move"]
    ma_fast = q["ma_fast"]

    if side == "CALL":
        sl_candidate = min(q["short_low"], ma_fast) - (step * 0.35)
        if sl_candidate >= p:
            sl_candidate = p - (step * 1.4)
        sl = round(sl_candidate, 2)

        t1_candidate = max(q["short_high"], p + (step * 2.2))
        if t1_candidate <= p * 1.004:
            t1_candidate = p + (step * 2.5)

        t2_candidate = max(q["chart_high"], t1_candidate + (step * 2.0))
        if t2_candidate <= t1_candidate:
            t2_candidate = t1_candidate + (step * 2.2)

        low_zone = min(p, ma_fast) if abs(p - ma_fast) <= step * 1.5 else p - (step * 0.3)
        high_zone = max(p, low_zone + (step * 0.4))
        return round(low_zone, 2), round(high_zone, 2), round(t1_candidate, 2), round(t2_candidate, 2), sl

    else:
        sl_candidate = max(q["short_high"], ma_fast) + (step * 0.35)
        if sl_candidate <= p:
            sl_candidate = p + (step * 1.4)
        sl = round(sl_candidate, 2)

        t1_candidate = min(q["short_low"], p - (step * 2.2))
        if t1_candidate >= p * 0.996:
            t1_candidate = p - (step * 2.5)

        t2_candidate = min(q["chart_low"], t1_candidate - (step * 2.0))
        if t2_candidate >= t1_candidate:
            t2_candidate = t1_candidate - (step * 2.2)

        high_zone = max(p, ma_fast) if abs(p - ma_fast) <= step * 1.5 else p + (step * 0.3)
        low_zone = min(p, high_zone - (step * 0.4))
        return round(low_zone, 2), round(high_zone, 2), round(t1_candidate, 2), round(t2_candidate, 2), sl


def compute_session_hold_info(now_ksa, current_price, target_price, avg_5m_move):
    dist = abs(target_price - current_price)
    bars_needed = max(2.0, dist / max(avg_5m_move, 0.01))
    est_mins = int(round(bars_needed * 5 * 1.35))
    hold_mins = max(25, min(MAX_HOLD_MINUTES, est_mins))

    session_end_dt = now_ksa.replace(hour=23, minute=55, second=0, microsecond=0)
    exit_dt = min(now_ksa + timedelta(minutes=hold_mins), session_end_dt)
    actual_mins = max(5, int((exit_dt - now_ksa).total_seconds() // 60))

    if actual_mins < 60:
        dur_txt = f"{actual_mins} دقيقة"
    else:
        hrs = round(actual_mins / 60, 1)
        dur_txt = f"{hrs} ساعة"

    return exit_dt, exit_dt.strftime("%I:%M %p"), dur_txt


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
    elif vol_ratio >= 1.0:
        score += 17
    elif vol_ratio >= 0.7:
        score += 14
    elif vol_ratio >= 0.3:
        score += 9
    else:
        score += 4

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

    if score >= 80 and vol_ratio >= MIN_VOL_RATIO:
        return "elite", "⭐ نخبة", score, "مسك موجة كاملة (سيولة داعمة)"
    elif score >= 50:
        return "strong", "🔥 ممتازة", score, "مسك أهداف متدرجة (سيولة داعمة)"
    else:
        return "good", "⚡ جيدة", score, "دخول خفيف (سيولة داعمة)"


def build_trade_reason(side, price, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct, vs_ma5_pct, short_high, short_low):
    if side == "CALL":
        ma_txt = "فوق MA5 وMA15" if (price >= ma_fast and ma_fast >= ma_slow) else f"فارق MA5 {vs_ma5_pct:+.2f}%"
        lvl_txt = f"قاع {short_low} / قمة {short_high}"
    else:
        ma_txt = "تحت MA5 وMA15" if (price <= ma_fast and ma_fast <= ma_slow) else f"فارق MA5 {vs_ma5_pct:+.2f}%"
        lvl_txt = f"قمة {short_high} / قاع {short_low}"
    vol_txt = f"{vol_ratio}x" if vol_ratio > 0 else "غير متاح"
    return f"3 شمعات {recent_3_pct:+.2f}% | {ma_txt} | {lvl_txt} | الحجم {vol_txt}"


def reset_daily_counters(date_str):
    global signal_count, stats, grade_counts, daily_trades_log, active_trading_date, active_trades, signaled_today
    signal_count = 0
    stats = {"wins": 0, "losses": 0}
    grade_counts = {"elite": 0, "strong": 0, "good": 0}
    daily_trades_log = []
    active_trades = {}
    signaled_today = set()
    active_trading_date = date_str


def update_trade_log_status(num, new_status):
    for item in daily_trades_log:
        if item["num"] == num:
            item["status"] = new_status
            break


def send_end_of_day_report(date_str, now_ksa):
    global eod_reported_date
    open_count = len(active_trades)
    decided = stats["wins"] + stats["losses"]
    win_rate = round((stats["wins"] / decided) * 100, 1) if decided > 0 else 0.0

    if daily_trades_log:
        companies_lines = "\n".join(
            f"#{t['num']} {t['ticker']} ({t['side']}) [{t['grade']}] — {t['status']}"
            for t in daily_trades_log
        )
    else:
        companies_lines = "لا توجد صفقات مسجلة اليوم."

    msg = (
        f"📊 تقرير نهاية اليوم ({date_str})\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 أسماء الشركات وصفقات اليوم:\n{companies_lines}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📌 إجمالي صفقات اليوم: {signal_count}\n"
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


def monitor_active_trades(now_ksa):
    closed_tickers = []
    for ticker, tr in list(active_trades.items()):
        try:
            q = fetch_quote_and_analysis(ticker)
            if not q:
                continue
            p = q["price"]
            num = tr["num"]
            side = tr["side"]
            dot = "🟢" if side == "CALL" else "🔴"
            expired_hold = now_ksa >= tr["exit_dt"]

            if side == "CALL":
                if not tr["t1_hit"] and p >= tr["t1"]:
                    tr["t1_hit"] = True
                    stats["wins"] += 1
                    update_trade_log_status(num, f"حقق الهدف 1 ({p}) ومستمر للهدف 2")
                    send_tg(
                        f"🎯 {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"حقق الهدف 1 عند {p} ومستمر للهدف 2 ({tr['t2']}) حتى {tr['exit_time_str']}"
                    )
                    time.sleep(1.1)
                if p >= tr["t2"]:
                    if not tr["t1_hit"]:
                        stats["wins"] += 1
                    stats["wins"] += 1
                    update_trade_log_status(num, f"حقق كل الأهداف ({p})")
                    send_tg(
                        f"✅ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"حقق الهدف 2 وأغلقت الصفقة بالكامل عند {p}"
                    )
                    closed_tickers.append(ticker)
                    time.sleep(1.1)
                elif p <= tr["sl"]:
                    stats["losses"] += 1
                    update_trade_log_status(num, f"ضرب الوقف ({p})")
                    send_tg(
                        f"❌ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"ضرب الوقف عند {p}"
                    )
                    closed_tickers.append(ticker)
                    time.sleep(1.1)
                elif expired_hold:
                    status_txt = f"انتهت مدة الجلوس بعد الهدف 1 ({p})" if tr["t1_hit"] else f"انتهت مدة الجلوس ({p})"
                    update_trade_log_status(num, status_txt)
                    send_tg(
                        f"⌛ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"انتهت مدة الجلوس ({tr['exit_time_str']}) والسعر الآن {p}"
                    )
                    closed_tickers.append(ticker)
                    time.sleep(1.1)
            else:
                if not tr["t1_hit"] and p <= tr["t1"]:
                    tr["t1_hit"] = True
                    stats["wins"] += 1
                    update_trade_log_status(num, f"حقق الهدف 1 ({p}) ومستمر للهدف 2")
                    send_tg(
                        f"🎯 {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"حقق الهدف 1 عند {p} ومستمر للهدف 2 ({tr['t2']}) حتى {tr['exit_time_str']}"
                    )
                    time.sleep(1.1)
                if p <= tr["t2"]:
                    if not tr["t1_hit"]:
                        stats["wins"] += 1
                    stats["wins"] += 1
                    update_trade_log_status(num, f"حقق كل الأهداف ({p})")
                    send_tg(
                        f"✅ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"حقق الهدف 2 وأغلقت الصفقة بالكامل عند {p}"
                    )
                    closed_tickers.append(ticker)
                    time.sleep(1.1)
                elif p >= tr["sl"]:
                    stats["losses"] += 1
                    update_trade_log_status(num, f"ضرب الوقف ({p})")
                    send_tg(
                        f"❌ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"ضرب الوقف عند {p}"
                    )
                    closed_tickers.append(ticker)
                    time.sleep(1.1)
                elif expired_hold:
                    status_txt = f"انتهت مدة الجلوس بعد الهدف 1 ({p})" if tr["t1_hit"] else f"انتهت مدة الجلوس ({p})"
                    update_trade_log_status(num, status_txt)
                    send_tg(
                        f"⌛ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"انتهت مدة الجلوس ({tr['exit_time_str']}) والسعر الآن {p}"
                    )
                    closed_tickers.append(ticker)
                    time.sleep(1.1)
        except Exception as e:
            print(f"Monitor error {ticker}: {e}")

    for t in closed_tickers:
        active_trades.pop(t, None)


def format_trade_message(prefix, num, ticker, side, grade_label, score, sizing_hint, p, pct, entry_low, entry_high, t1, t2, sl, hold_dur_txt, exit_time_str, reason_txt):
    dot = "🟢" if side == "CALL" else "🔴"
    pct_txt = f"+{pct:.2f}%" if pct >= 0 else f"-{abs(pct):.2f}%"
    entry_txt = f"{entry_low} - {entry_high}" if entry_low != entry_high else f"{entry_low}"
    return (
        f"{prefix}{dot} صفقة #{num} | {ticker} ({side})\n"
        f"التصنيف: {grade_label} ({score}/100) — {sizing_hint}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"السعر الآن: {p} | اليوم: {pct_txt}\n"
        f"منطقة الدخول: {entry_txt}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"الهدف 1: {t1}\n"
        f"الهدف 2: {t2}\n"
        f"الوقف: {sl}\n"
        f"الجلوس في الجلسة: حتى {exit_time_str} ({hold_dur_txt})\n"
        f"━━━━━━━━━━━━━━━\n"
        f"السبب: {reason_txt}"
    )


def scan_new_setups(now_ksa):
    global signal_count, last_heartbeat_ts
    ok_count = 0
    missing = []
    top_move = ("-", 0.0)
    sent_this_scan = 0

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

            if time.time() < tg_blocked_until or sent_this_scan >= 4:
                continue

            if ticker in signaled_today or ticker in active_trades:
                continue

            vol_ratio = q["vol_ratio"]
            if vol_ratio < MIN_VOL_RATIO:
                continue

            ma_fast = q["ma_fast"]
            ma_slow = q["ma_slow"]
            recent_3_pct = q["recent_3_pct"]
            vs_ma5_pct = q["vs_ma5_pct"]
            vs_ma15_pct = q["vs_ma15_pct"]

            bullish_setup = (
                recent_3_pct >= 0.03
                or (vs_ma5_pct >= 0.03 and recent_3_pct >= 0.0)
                or (p >= ma_fast and recent_3_pct >= 0.02)
                or (vs_ma15_pct >= 0.08 and recent_3_pct >= 0.01)
            )
            bearish_setup = (
                recent_3_pct <= -0.03
                or (vs_ma5_pct <= -0.03 and recent_3_pct <= 0.0)
                or (p <= ma_fast and recent_3_pct <= -0.02)
                or (vs_ma15_pct <= -0.08 and recent_3_pct <= -0.01)
            )

            if bullish_setup:
                entry_low, entry_high, t1, t2, sl = compute_chart_levels("CALL", q)
                exit_dt, exit_time_str, hold_dur_txt = compute_session_hold_info(now_ksa, p, t2, q["avg_5m_move"])

                signal_count += 1
                sent_this_scan += 1
                signaled_today.add(ticker)

                grade_key, grade_label, score, sizing_hint = score_and_grade(
                    "CALL", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct
                )
                grade_counts[grade_key] += 1

                reason_txt = build_trade_reason(
                    "CALL", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct, vs_ma5_pct,
                    q["short_high"], q["short_low"]
                )

                active_trades[ticker] = {
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "CALL",
                    "t1": t1,
                    "t2": t2,
                    "sl": sl,
                    "t1_hit": False,
                    "exit_dt": exit_dt,
                    "exit_time_str": exit_time_str
                }
                daily_trades_log.append({
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "CALL",
                    "grade": grade_label,
                    "status": f"متابعة حتى {exit_time_str}"
                })

                prefix = "🚨 فرصة نخبة!\n" if grade_key == "elite" else ""
                msg = format_trade_message(
                    prefix, signal_count, ticker, "CALL", grade_label, score, sizing_hint,
                    p, pct, entry_low, entry_high, t1, t2, sl, hold_dur_txt, exit_time_str, reason_txt
                )
                send_tg(msg)
                time.sleep(1.2)

            elif bearish_setup:
                entry_low, entry_high, t1, t2, sl = compute_chart_levels("PUT", q)
                exit_dt, exit_time_str, hold_dur_txt = compute_session_hold_info(now_ksa, p, t2, q["avg_5m_move"])

                signal_count += 1
                sent_this_scan += 1
                signaled_today.add(ticker)

                grade_key, grade_label, score, sizing_hint = score_and_grade(
                    "PUT", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct
                )
                grade_counts[grade_key] += 1

                reason_txt = build_trade_reason(
                    "PUT", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct, vs_ma5_pct,
                    q["short_high"], q["short_low"]
                )

                active_trades[ticker] = {
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "PUT",
                    "t1": t1,
                    "t2": t2,
                    "sl": sl,
                    "t1_hit": False,
                    "exit_dt": exit_dt,
                    "exit_time_str": exit_time_str
                }
                daily_trades_log.append({
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "PUT",
                    "grade": grade_label,
                    "status": f"متابعة حتى {exit_time_str}"
                })

                prefix = "🚨 فرصة نخبة!\n" if grade_key == "elite" else ""
                msg = format_trade_message(
                    prefix, signal_count, ticker, "PUT", grade_label, score, sizing_hint,
                    p, pct, entry_low, entry_high, t1, t2, sl, hold_dur_txt, exit_time_str, reason_txt
                )
                send_tg(msg)
                time.sleep(1.2)
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
                monitor_active_trades(now_ksa)
                scan_new_setups(now_ksa)
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
    send_tg("⚡ تم تشغيل البوت بنسخة السيولة في كل الدرجات.")
    main_loop()
