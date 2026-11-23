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


def find_swing_highs_lows(highs, lows):
    swing_highs = []
    swing_lows = []
    n = len(highs)
    for i in range(1, n - 1):
        if highs[i] > highs[i - 1] and highs[i] >= highs[i + 1]:
            swing_highs.append(float(highs[i]))
        if lows[i] < lows[i - 1] and lows[i] <= lows[i + 1]:
            swing_lows.append(float(lows[i]))
    return swing_highs, swing_lows


def fetch_daily_avg_move(ticker, fallback_price):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=3mo"
    try:
        r = SESSION.get(url, timeout=6)
        if r.status_code != 200:
            return max(fallback_price * 0.015, 0.05)
        data = r.json()
        results = (data.get("chart") or {}).get("result") or []
        if not results:
            return max(fallback_price * 0.015, 0.05)
        quote = (((results[0] or {}).get("indicators") or {}).get("quote") or [{}])[0] or {}
        d_highs = [float(h) for h in (quote.get("high") or []) if h is not None]
        d_lows = [float(l) for l in (quote.get("low") or []) if l is not None]
        daily_ranges = [h - l for h, l in zip(d_highs[-20:], d_lows[-20:]) if h > l]
        if daily_ranges:
            return max(sum(daily_ranges) / len(daily_ranges), fallback_price * 0.008)
    except Exception:
        pass
    return max(fallback_price * 0.015, 0.05)


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

        closes = [float(c) for c in (quote.get("close") or []) if c is not None]
        lows = [float(l) for l in (quote.get("low") or []) if l is not None]
        highs = [float(h) for h in (quote.get("high") or []) if h is not None]
        volumes = [float(v) for v in (quote.get("volume") or []) if v is not None]

        if len(closes) < 10 or len(highs) < 10 or len(lows) < 10:
            return None

        price = float(price)
        prev_close = float(prev_close)

        pct = ((price - prev_close) / prev_close) * 100
        ma_fast = sum(closes[-5:]) / 5.0
        ma_slow = sum(closes[-15:]) / min(len(closes), 15)

        ref_3 = closes[-3] if len(closes) >= 3 else closes[0]
        raw_3_pct = ((closes[-1] - ref_3) / ref_3) * 100 if ref_3 > 0 else 0.0
        recent_3_change_pct = max(-8.0, min(8.0, raw_3_pct))

        last_1_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100 if len(closes) >= 2 and closes[-2] > 0 else 0.0
        prev_1_pct = ((closes[-2] - closes[-3]) / closes[-3]) * 100 if len(closes) >= 3 and closes[-3] > 0 else 0.0

        vs_ma5_pct = ((price - ma_fast) / ma_fast) * 100 if ma_fast > 0 else 0.0
        vs_ma15_pct = ((price - ma_slow) / ma_slow) * 100 if ma_slow > 0 else 0.0

        valid_vols = [v for v in volumes[:-1] if v > 0]
        avg_vol = (sum(valid_vols) / len(valid_vols)) if valid_vols else 0.0
        last_vol = volumes[-1] if volumes else 0.0
        vol_ratio = round((last_vol / avg_vol), 2) if (avg_vol > 0 and last_vol > 0) else 0.0

        recent_highs = highs[-24:] if len(highs) >= 24 else highs
        recent_lows = lows[-24:] if len(lows) >= 24 else lows
        swing_highs, swing_lows = find_swing_highs_lows(recent_highs, recent_lows)

        short_high = max(highs[-6:])
        short_low = min(lows[-6:])
        chart_high = max(recent_highs)
        chart_low = min(recent_lows)

        chop_range_pct = ((short_high - short_low) / short_low) * 100 if short_low > 0 else 0.0
        ranges = [h - l for h, l in zip(highs[-15:], lows[-15:]) if h > l and (h - l) <= price * 0.03]
        avg_5m_move = max(sum(ranges) / len(ranges), price * 0.0012) if ranges else price * 0.0018
        avg_daily_move = fetch_daily_avg_move(ticker, price)

        return {
            "price": round(price, 2),
            "pct": round(pct, 2),
            "ma_fast": round(ma_fast, 2),
            "ma_slow": round(ma_slow, 2),
            "recent_3_pct": round(recent_3_change_pct, 2),
            "last_1_pct": round(last_1_pct, 2),
            "prev_1_pct": round(prev_1_pct, 2),
            "chop_range_pct": round(chop_range_pct, 2),
            "vs_ma5_pct": round(vs_ma5_pct, 2),
            "vs_ma15_pct": round(vs_ma15_pct, 2),
            "vol_ratio": vol_ratio,
            "short_high": round(short_high, 2),
            "short_low": round(short_low, 2),
            "chart_high": round(chart_high, 2),
            "chart_low": round(chart_low, 2),
            "swing_highs": [round(x, 2) for x in swing_highs],
            "swing_lows": [round(x, 2) for x in swing_lows],
            "avg_5m_move": float(avg_5m_move),
            "avg_daily_move": float(avg_daily_move)
        }
    except Exception as e:
        print(f"Analysis error {ticker}: {e}")
        return None


def is_clean_candle_flow(side, q):
    if q["chop_range_pct"] < 0.25:
        return False

    prev_1 = q["prev_1_pct"]
    last_1 = q["last_1_pct"]

    if side == "CALL":
        spike_then_fade = prev_1 >= 0.80 and last_1 <= -0.35
        dead_last_candle = last_1 < -0.15
        return not (spike_then_fade or dead_last_candle)
    else:
        spike_then_fade = prev_1 <= -0.80 and last_1 >= 0.35
        dead_last_candle = last_1 > 0.15
        return not (spike_then_fade or dead_last_candle)


def compute_chart_levels(side, q):
    p = q["price"]
    step = q["avg_5m_move"]
    ma_fast = q["ma_fast"]
    buffer_amt = max(step * 0.35, p * 0.001)

    if side == "CALL":
        lows_below = sorted([x for x in q["swing_lows"] if x < p], reverse=True)
        if lows_below:
            sl_base = lows_below[1] if len(lows_below) > 1 else lows_below[0]
            sl = round(sl_base - buffer_amt, 2)
        else:
            sl = round(min(q["short_low"], ma_fast) - buffer_amt, 2)
        if sl >= p:
            sl = round(p - max(step * 1.3, p * 0.0035), 2)

        highs_above = sorted([x for x in q["swing_highs"] if x > p])
        min_t1 = p + max(step * 1.6, p * 0.003)
        above_min_t1 = [x for x in highs_above if x >= min_t1]
        if above_min_t1:
            t1 = round(above_min_t1[0], 2)
        elif highs_above:
            t1 = round(max(highs_above[-1], min_t1), 2)
        else:
            t1 = round(max(q["short_high"], min_t1), 2)

        above_t1 = [x for x in highs_above if x > t1 + max(step * 0.9, p * 0.0018)]
        if above_t1:
            t2 = round(above_t1[0], 2)
        else:
            t2 = round(max(q["chart_high"], t1 + max(step * 1.6, p * 0.003)), 2)

        low_zone = round(min(p, ma_fast) if abs(p - ma_fast) <= step * 1.2 else p - (step * 0.2), 2)
        high_zone = round(max(p, low_zone + (step * 0.3)), 2)
        return low_zone, high_zone, t1, t2, sl

    else:
        highs_above = sorted([x for x in q["swing_highs"] if x > p])
        if highs_above:
            sl_base = highs_above[1] if len(highs_above) > 1 else highs_above[0]
            sl = round(sl_base + buffer_amt, 2)
        else:
            sl = round(max(q["short_high"], ma_fast) + buffer_amt, 2)
        if sl <= p:
            sl = round(p + max(step * 1.3, p * 0.0035), 2)

        lows_below = sorted([x for x in q["swing_lows"] if x < p], reverse=True)
        max_t1 = p - max(step * 1.6, p * 0.003)
        below_max_t1 = [x for x in lows_below if x <= max_t1]
        if below_max_t1:
            t1 = round(below_max_t1[0], 2)
        elif lows_below:
            t1 = round(min(lows_below[-1], max_t1), 2)
        else:
            t1 = round(min(q["short_low"], max_t1), 2)

        below_t1 = [x for x in lows_below if x < t1 - max(step * 0.9, p * 0.0018)]
        if below_t1:
            t2 = round(below_t1[0], 2)
        else:
            t2 = round(min(q["chart_low"], t1 - max(step * 1.6, p * 0.003)), 2)

        high_zone = round(max(p, ma_fast) if abs(p - ma_fast) <= step * 1.2 else p + (step * 0.2), 2)
        low_zone = round(min(p, high_zone - (step * 0.3)), 2)
        return low_zone, high_zone, t1, t2, sl


def estimate_duration_label(now_ksa, current_price, target_price, avg_daily_move):
    dist = abs(target_price - current_price)
    day_move = max(avg_daily_move, 0.01)
    est_days = dist / day_move

    if est_days <= 0.15:
        label = "ساعة"
        max_days = 1
    elif est_days <= 0.35:
        label = "ساعتين"
        max_days = 1
    elif est_days <= 0.65:
        label = "3 ساعات"
        max_days = 1
    elif est_days <= 1.15:
        label = "4 ساعات"
        max_days = 2
    elif est_days <= 1.85:
        label = "يوم"
        max_days = 2
    elif est_days <= 2.6:
        label = "يومين"
        max_days = 3
    elif est_days <= 4.0:
        label = "3 أيام"
        max_days = 5
    elif est_days <= 8.0:
        label = "أسبوع"
        max_days = 10
    elif est_days <= 22.0:
        label = "شهر"
        max_days = 35
    else:
        label = "شهرين"
        max_days = 65

    exit_dt = now_ksa + timedelta(days=max_days)
    return exit_dt, label


def score_and_grade(side, price, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct):
    score = 0
    abs_pct = abs(pct)

    if abs_pct >= 2.0:
        score += 25
    elif abs_pct >= 1.0:
        score += 18
    elif abs_pct >= 0.5:
        score += 12
    else:
        score += 6

    trend_aligned = False
    if side == "CALL":
        if price > ma_fast and ma_fast >= ma_slow:
            score += 30
            trend_aligned = True
        elif price >= ma_fast:
            score += 18
        else:
            score += 6
    else:
        if price < ma_fast and ma_fast <= ma_slow:
            score += 30
            trend_aligned = True
        elif price <= ma_fast:
            score += 18
        else:
            score += 6

    if vol_ratio >= 1.3:
        score += 20
    elif vol_ratio >= 1.0:
        score += 15
    elif vol_ratio >= 0.6:
        score += 9
    else:
        score += 4

    strong_3_candles = False
    if side == "CALL":
        if recent_3_pct >= 0.25:
            score += 25
            strong_3_candles = True
        elif recent_3_pct >= 0.12:
            score += 16
        elif recent_3_pct >= 0.0:
            score += 8
        else:
            score += 2
    else:
        if recent_3_pct <= -0.25:
            score += 25
            strong_3_candles = True
        elif recent_3_pct <= -0.12:
            score += 16
        elif recent_3_pct <= 0.0:
            score += 8
        else:
            score += 2

    score = min(100, score)

    if score >= 85 and trend_aligned and strong_3_candles and vol_ratio >= 1.0:
        return "elite", "⭐ نخبة", score, "مسك موجة كاملة"
    elif score >= 62:
        return "strong", "🔥 ممتازة", score, "مسك أهداف متدرجة"
    else:
        return "good", "⚡ جيدة", score, "دخول خفيف"


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
        best_trade = max(daily_trades_log, key=lambda x: x.get("score", 0))
        best_txt = f"#{best_trade['num']} {best_trade['ticker']} ({best_trade['score']}/100)"

        calls_cnt = sum(1 for t in daily_trades_log if t["side"] == "CALL")
        puts_cnt = sum(1 for t in daily_trades_log if t["side"] == "PUT")
        if calls_cnt > puts_cnt:
            bias_txt = f"غالبية CALL ({calls_cnt} مقابل {puts_cnt})"
        elif puts_cnt > calls_cnt:
            bias_txt = f"غالبية PUT ({puts_cnt} مقابل {calls_cnt})"
        else:
            bias_txt = f"متوازن ({calls_cnt} CALL / {puts_cnt} PUT)"
    else:
        companies_lines = "لا توجد صفقات مسجلة اليوم."
        best_txt = "لا يوجد"
        bias_txt = "لا يوجد"

    msg = (
        f"📊 تقرير نهاية اليوم ({date_str})\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 أسماء الشركات وصفقات اليوم:\n{companies_lines}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏆 أقوى صفقة اليوم: {best_txt}\n"
        f"🧭 غالبية الاتجاه: {bias_txt}\n"
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
                        f"حقق الهدف 1 عند {p} ومستمر للهدف 2 ({tr['t2']})"
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
                    status_txt = f"انتهى الإطار بعد الهدف 1 ({p})" if tr["t1_hit"] else f"انتهى الإطار ({p})"
                    update_trade_log_status(num, status_txt)
                    send_tg(
                        f"⌛ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"انتهى الإطار ({tr['dur_label']}) والسعر الآن {p}"
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
                        f"حقق الهدف 1 عند {p} ومستمر للهدف 2 ({tr['t2']})"
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
                    status_txt = f"انتهى الإطار بعد الهدف 1 ({p})" if tr["t1_hit"] else f"انتهى الإطار ({p})"
                    update_trade_log_status(num, status_txt)
                    send_tg(
                        f"⌛ {ticker} | صفقة #{num} ({side}) {dot}\n"
                        f"انتهى الإطار ({tr['dur_label']}) والسعر الآن {p}"
                    )
                    closed_tickers.append(ticker)
                    time.sleep(1.1)
        except Exception as e:
            print(f"Monitor error {ticker}: {e}")

    for t in closed_tickers:
        active_trades.pop(t, None)


def format_trade_message(prefix, num, ticker, side, grade_label, score, sizing_hint, p, pct, entry_low, entry_high, t1, t2, sl, dur_label, reason_txt):
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
        f"المدة: {dur_label}\n"
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

            if time.time() < tg_blocked_until or sent_this_scan >= 2:
                continue

            if ticker in signaled_today or ticker in active_trades:
                continue

            ma_fast = q["ma_fast"]
            ma_slow = q["ma_slow"]
            vol_ratio = q["vol_ratio"]
            recent_3_pct = q["recent_3_pct"]
            vs_ma5_pct = q["vs_ma5_pct"]

            bullish_setup = (
                recent_3_pct >= 0.16
                and p >= ma_fast
                and is_clean_candle_flow("CALL", q)
            )
            bearish_setup = (
                recent_3_pct <= -0.16
                and p <= ma_fast
                and is_clean_candle_flow("PUT", q)
            )

            if bullish_setup:
                entry_low, entry_high, t1, t2, sl = compute_chart_levels("CALL", q)
                grade_key, grade_label, score, sizing_hint = score_and_grade(
                    "CALL", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct
                )
                exit_dt, dur_label = estimate_duration_label(
                    now_ksa, p, t2, q["avg_daily_move"]
                )

                signal_count += 1
                sent_this_scan += 1
                signaled_today.add(ticker)
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
                    "dur_label": dur_label
                }
                daily_trades_log.append({
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "CALL",
                    "grade": grade_label,
                    "score": score,
                    "status": f"متابعة ({dur_label})"
                })

                prefix = "🚨 فرصة نخبة!\n" if grade_key == "elite" else ""
                msg = format_trade_message(
                    prefix, signal_count, ticker, "CALL", grade_label, score, sizing_hint,
                    p, pct, entry_low, entry_high, t1, t2, sl, dur_label, reason_txt
                )
                send_tg(msg)
                time.sleep(1.2)

            elif bearish_setup:
                entry_low, entry_high, t1, t2, sl = compute_chart_levels("PUT", q)
                grade_key, grade_label, score, sizing_hint = score_and_grade(
                    "PUT", p, pct, ma_fast, ma_slow, vol_ratio, recent_3_pct
                )
                exit_dt, dur_label = estimate_duration_label(
                    now_ksa, p, t2, q["avg_daily_move"]
                )

                signal_count += 1
                sent_this_scan += 1
                signaled_today.add(ticker)
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
                    "dur_label": dur_label
                }
                daily_trades_log.append({
                    "num": signal_count,
                    "ticker": ticker,
                    "side": "PUT",
                    "grade": grade_label,
                    "score": score,
                    "status": f"متابعة ({dur_label})"
                })

                prefix = "🚨 فرصة نخبة!\n" if grade_key == "elite" else ""
                msg = format_trade_message(
                    prefix, signal_count, ticker, "PUT", grade_label, score, sizing_hint,
                    p, pct, entry_low, entry_high, t1, t2, sl, dur_label, reason_txt
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
    send_tg("⚡ تم تشغيل البوت بالمدد الزمنية المحددة وتقرير نهاية اليوم.")
    main_loop()
