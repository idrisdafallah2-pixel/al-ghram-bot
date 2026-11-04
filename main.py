# -*- coding: utf-8 -*-
"""
Telegram Signals Bot - Price Action / Liquidity / Volume / Geometry
- بدون مؤشرات | BUY STOP / SELL STOP فقط | R:R = 1:2
- جلستا لندن ونيويورك فقط | صفقة واحدة في كل مرة
- أسعار CFD من OANDA (حساب Demo مجاني)

Environment variables:
  TELEGRAM_TOKEN, OANDA_TOKEN, OANDA_ACCOUNT_ID
  CHAT_IDS (مستحسن)، ACCOUNT_BALANCE، RISK_PCT، MIN_SCORE، SYMBOLS
"""
import os
import json
import time
import asyncio
import logging
import threading
from statistics import mean
from datetime import datetime, timezone, time as dtime
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("signals-bot")

# ───────────── الإعدادات ─────────────
TOKEN = os.environ["TELEGRAM_TOKEN"]
OANDA_TOKEN = os.environ["OANDA_TOKEN"]
OANDA_ACCOUNT = os.environ["OANDA_ACCOUNT_ID"]
OANDA_HOST = os.getenv("OANDA_HOST", "https://api-fxpractice.oanda.com")
CHAT_IDS = {int(x) for x in os.getenv("CHAT_IDS", "").replace(" ", "").split(",") if x}
BALANCE = float(os.getenv("ACCOUNT_BALANCE", "1000"))
RISK_PCT = float(os.getenv("RISK_PCT", "1"))
MIN_SCORE = int(os.getenv("MIN_SCORE", "75"))
RR = 2.0
MAX_SIGNALS_DAY = int(os.getenv("MAX_SIGNALS_DAY", "8"))
MAX_LOSSES_DAY = int(os.getenv("MAX_LOSSES_DAY", "3"))
PENDING_EXPIRY_MIN = int(os.getenv("PENDING_EXPIRY_MIN", "120"))
COOLDOWN_MIN = int(os.getenv("COOLDOWN_MIN", "30"))
BE_AT_1R = os.getenv("BE_AT_1R", "false").lower() == "true"
SCAN_SEC = int(os.getenv("SCAN_SEC", "30"))
MONITOR_SEC = int(os.getenv("MONITOR_SEC", "10"))
STATE_FILE = os.getenv("STATE_FILE", "state.json")

LON, NY = ZoneInfo("Europe/London"), ZoneInfo("America/New_York")

ALL_SYMBOLS = {
    "XAUUSD": dict(inst="XAU_USD",    digits=2, pip=0.1,    contract=100,    quote="USD"),
    "EURUSD": dict(inst="EUR_USD",    digits=5, pip=0.0001, contract=100000, quote="USD"),
    "GBPUSD": dict(inst="GBP_USD",    digits=5, pip=0.0001, contract=100000, quote="USD"),
    "USDJPY": dict(inst="USD_JPY",    digits=3, pip=0.01,   contract=100000, quote="JPY"),
    "NAS100": dict(inst="NAS100_USD", digits=1, pip=1.0,    contract=1,      quote="USD"),
    "US30":   dict(inst="US30_USD",   digits=1, pip=1.0,    contract=1,      quote="USD"),
}
_enabled = [s.strip().upper() for s in os.getenv("SYMBOLS", ",".join(ALL_SYMBOLS)).split(",")]
SYMBOLS = {k: v for k, v in ALL_SYMBOLS.items() if k in _enabled}

HDR = {"Authorization": f"Bearer {OANDA_TOKEN}"}
LOCK = asyncio.Lock()

# ───────────── الحالة ─────────────
state = dict(next_id=1, signal=None, day=None, day_signals=0, day_losses=0,
             stats=dict(win=0, loss=0, be=0, cancel=0, r=0.0), cooldown={}, chats=[])


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state.update(json.load(f))
    except Exception:
        pass


def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception as e:
        log.warning("save_state: %s", e)


def now_utc():
    return datetime.now(timezone.utc)


def reset_day():
    d = now_utc().strftime("%Y-%m-%d")
    if state["day"] != d:
        state.update(day=d, day_signals=0, day_losses=0)
        save_state()


def fmt(sym, p):
    return f"{p:.{SYMBOLS[sym]['digits']}f}"


def session_info(dt=None):
    dt = dt or now_utc()
    l, n = dt.astimezone(LON), dt.astimezone(NY)

    def left(x, end):
        return (end.hour * 60 + end.minute) - (x.hour * 60 + x.minute)

    act = []
    if l.weekday() < 5 and dtime(8, 0) <= l.time() < dtime(16, 0):
        act.append(("لندن", left(l, dtime(16, 0))))
    if n.weekday() < 5 and dtime(8, 30) <= n.time() < dtime(16, 0):
        act.append(("نيويورك", left(n, dtime(16, 0))))
    return max(act, key=lambda x: x[1]) if act else None


# ───────────── بيانات OANDA (CFD) ─────────────
async def get_candles(http, inst, gran, count):
    r = await http.get(f"{OANDA_HOST}/v3/instruments/{inst}/candles",
                       params={"granularity": gran, "count": count, "price": "M"}, headers=HDR)
    r.raise_for_status()
    out = []
    for c in r.json()["candles"]:
        if not c.get("complete"):
            continue
        m = c["mid"]
        out.append(dict(
            dt=datetime.strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc),
            o=float(m["o"]), h=float(m["h"]), l=float(m["l"]), c=float(m["c"]), v=int(c["volume"])))
    return out


_cache = {}


async def cached(http, inst, gran, count, ttl):
    k, t = (inst, gran), time.time()
    if k in _cache and t - _cache[k][0] < ttl:
        return _cache[k][1]
    d = await get_candles(http, inst, gran, count)
    _cache[k] = (t, d)
    return d


async def get_prices(http, syms):
    r = await http.get(f"{OANDA_HOST}/v3/accounts/{OANDA_ACCOUNT}/pricing",
                       params={"instruments": ",".join(SYMBOLS[s]["inst"] for s in syms)}, headers=HDR)
    r.raise_for_status()
    inv = {SYMBOLS[s]["inst"]: s for s in syms}
    out = {}
    for p in r.json()["prices"]:
        if p.get("bids") and p.get("asks") and p["instrument"] in inv:
            out[inv[p["instrument"]]] = (float(p["bids"][0]["price"]), float(p["asks"][0]["price"]),
                                         p.get("tradeable", True))
    return out


# ───────────── محرك التحليل (Price Action) ─────────────
def pivots(cs, k=3):
    hi, lo = [], []
    for i in range(k, len(cs) - k):
        seg = cs[i - k:i + k + 1]
        if cs[i]["h"] == max(x["h"] for x in seg):
            hi.append((i, cs[i]["h"]))
        if cs[i]["l"] == min(x["l"] for x in seg):
            lo.append((i, cs[i]["l"]))
    return hi, lo


def bias_of(hi, lo):
    if len(hi) < 2 or len(lo) < 2:
        return "range"
    if hi[-1][1] > hi[-2][1] and lo[-1][1] > lo[-2][1]:
        return "up"
    if hi[-1][1] < hi[-2][1] and lo[-1][1] < lo[-2][1]:
        return "down"
    return "range"


def cluster(piv, tol, side):
    groups = []
    for p in sorted(piv, key=lambda x: x[1]):
        if groups and abs(p[1] - groups[-1][-1][1]) <= tol:
            groups[-1].append(p)
        else:
            groups.append([p])
    out = []
    for g in groups:
        price = max(x[1] for x in g) if side == "high" else min(x[1] for x in g)
        name = ("EQH" if side == "high" else "EQL") + f"x{len(g)}" if len(g) >= 2 else "SWING"
        out.append(dict(p=price, side=side, name=name, w=len(g)))
    return out


def build_levels(m15, d1, hi, lo, tol):
    lv = []
    pd = d1[-1]
    lv += [dict(p=pd["h"], side="high", name="PDH", w=3), dict(p=pd["l"], side="low", name="PDL", w=3)]
    today = m15[-1]["dt"].date()
    asia = [c for c in m15 if c["dt"].date() == today and c["dt"].hour < 7]
    if len(asia) >= 12:
        lv += [dict(p=max(c["h"] for c in asia), side="high", name="ASIA-H", w=2),
               dict(p=min(c["l"] for c in asia), side="low", name="ASIA-L", w=2)]
    lv += cluster(hi, tol, "high") + cluster(lo, tol, "low")
    return lv


def trade_levels(side, top, bot, avg, spread, bid, ask, levels):
    buf = max(spread * 1.5, 0.05 * avg)  # فرق التفعيل
    if side == "BUY":
        entry, sl = top + buf, bot - buf
        risk = entry - sl
    else:
        entry, sl = bot - buf, top + buf
        risk = sl - entry
    if risk < 0.6 * avg:
        risk = 0.6 * avg
        sl = entry - risk if side == "BUY" else entry + risk
    if risk > 4 * avg or risk < 4 * spread:
        return None
    if side == "BUY" and ask >= entry - spread * 0.5:
        return None
    if side == "SELL" and bid <= entry + spread * 0.5:
        return None
    tp = entry + RR * risk if side == "BUY" else entry - RR * risk
    if side == "BUY":
        ahead = [L["p"] for L in levels if L["p"] > entry]
        if ahead and min(ahead) < entry + 1.8 * risk:
            return None
    else:
        ahead = [L["p"] for L in levels if L["p"] < entry]
        if ahead and max(ahead) > entry - 1.8 * risk:
            return None
    return dict(entry=entry, sl=sl, tp=tp, risk=risk, buf=buf)


BIAS_AR = {"up": "صاعد", "down": "هابط", "range": "عرضي"}


def setup_sweep(sym, m15, levels, bias, avg, spread, bid, ask):
    out = []
    for k in (1, 2):
        c = m15[-k]
        after = m15[len(m15) - k + 1:]
        rng = c["h"] - c["l"]
        if rng < 0.8 * avg:
            continue
        base = m15[-k - 20:-k]
        vavg = mean(x["v"] for x in base) or 1
        vr = c["v"] / vavg
        vpts = 20 if vr >= 1.5 else 10 if vr >= 1.2 else 0
        for side in ("BUY", "SELL"):
            for L in levels:
                if side == "BUY" and L["side"] == "low":
                    if not (c["l"] < L["p"] - 0.05 * avg and c["c"] > L["p"]):
                        continue
                    wick = min(c["o"], c["c"]) - c["l"]
                    if any(x["l"] < c["l"] for x in after):
                        continue
                    bp = 15 if bias == "up" else 7 if bias == "range" else 0
                elif side == "SELL" and L["side"] == "high":
                    if not (c["h"] > L["p"] + 0.05 * avg and c["c"] < L["p"]):
                        continue
                    wick = c["h"] - max(c["o"], c["c"])
                    if any(x["h"] > c["h"] for x in after):
                        continue
                    bp = 15 if bias == "down" else 7 if bias == "range" else 0
                else:
                    continue
                if wick / rng < 0.4:
                    continue
                seg = [c] + after
                top, bot = max(x["h"] for x in seg), min(x["l"] for x in seg)
                t = trade_levels(side, top, bot, avg, spread, bid, ask, levels)
                if not t:
                    continue
                score = 30 + (15 if wick / rng >= 0.55 else 8) + vpts + bp + (10 if L["w"] >= 2 else 4) + 10
                out.append(dict(symbol=sym, side=side, score=score, setup="كنس سيولة + رفض",
                                detail=f"كنس {L['name']} | فوليوم x{vr:.1f} | الاتجاه الأكبر: {BIAS_AR[bias]}", **t))
    return out


def setup_coil(sym, m15, levels, bias, avg, spread, bid, ask):
    w = m15[-10:]
    a, b = w[:5], w[5:]
    r1, r2 = mean(c["h"] - c["l"] for c in a), mean(c["h"] - c["l"] for c in b)
    if r1 <= 0 or r2 > 0.75 * r1:
        return []
    if not (max(c["h"] for c in a) > max(c["h"] for c in b) and min(c["l"] for c in a) < min(c["l"] for c in b)):
        return []
    top, bot = max(c["h"] for c in w[-6:]), min(c["l"] for c in w[-6:])
    v1, v2 = mean(c["v"] for c in a), mean(c["v"] for c in b)
    vpts = 15 if v2 < 0.85 * v1 else 0
    out = []
    for side in ("BUY", "SELL"):
        if side == "BUY":
            near = any(L["side"] == "low" and abs(bot - L["p"]) <= 2 * avg for L in levels)
            bp = 25 if bias == "up" else 10 if bias == "range" else 0
        else:
            near = any(L["side"] == "high" and abs(top - L["p"]) <= 2 * avg for L in levels)
            bp = 25 if bias == "down" else 10 if bias == "range" else 0
        if not near or bp == 0:
            continue
        t = trade_levels(side, top, bot, avg, spread, bid, ask, levels)
        if not t:
            continue
        score = 30 + vpts + 20 + bp + 10
        out.append(dict(symbol=sym, side=side, score=score, setup="انضغاط هندسي عند دعم/مقاومة",
                        detail=f"مثلث انضغاط | الاتجاه الأكبر: {BIAS_AR[bias]}", **t))
    return out


def analyze(sym, m15, h1, d1, bid, ask):
    if len(m15) < 60 or len(h1) < 80 or not d1:
        return []
    if (now_utc() - m15[-1]["dt"]).total_seconds() > 45 * 60:
        return []
    spread = ask - bid
    avg = mean(c["h"] - c["l"] for c in m15[-20:])
    h1avg = mean(c["h"] - c["l"] for c in h1[-24:])
    if avg <= 0 or spread > 0.35 * avg:
        return []
    hi, lo = pivots(h1[-150:], 3)
    bias = bias_of(hi, lo)
    levels = build_levels(m15, d1, hi, lo, h1avg * 0.25)
    return (setup_sweep(sym, m15, levels, bias, avg, spread, bid, ask)
            + setup_coil(sym, m15, levels, bias, avg, spread, bid, ask))


# ───────────── إدارة المخاطر والرسائل ─────────────
def lots_for(sym, price, risk_dist):
    s = SYMBOLS[sym]
    unit = s["contract"] / (price if s["quote"] == "JPY" else 1)
    lots = (BALANCE * RISK_PCT / 100) / (risk_dist * unit)
    return int(lots * 100) / 100


def signal_text(sig, bid, ask, title="🔔 إشارة جديدة"):
    sym = sig["symbol"]
    pip = SYMBOLS[sym]["pip"]
    buy = sig["side"] == "BUY"
    act = (sig["entry"] - ask) if buy else (bid - sig["entry"])
    lots = lots_for(sym, sig["entry"], sig["risk"])
    lots_line = (f"{lots:.2f} لوت (مخاطرة {RISK_PCT:g}% من {BALANCE:g}$)" if lots >= 0.01
                 else "الحد الأدنى 0.01 لوت يتجاوز نسبة المخاطرة — خفّض الحجم يدوياً")
    return (
        f"{title} #{sig['id']} — <b>{sym}</b>\n"
        f"{'🟢' if buy else '🔴'} <b>{sig['side']} STOP</b>\n"
        f"━━━━━━━━━━━━\n"
        f"📍 الدخول: <code>{fmt(sym, sig['entry'])}</code>\n"
        f"🛑 وقف الخسارة: <code>{fmt(sym, sig['sl'])}</code>\n"
        f"🎯 الهدف: <code>{fmt(sym, sig['tp'])}</code>\n"
        f"━━━━━━━━━━━━\n"
        f"السعر الآن: Bid {fmt(sym, bid)} / Ask {fmt(sym, ask)}\n"
        f"⚡ فرق التفعيل: {act / pip:.1f} نقطة ({fmt(sym, act)})\n"
        f"المخاطرة: {sig['risk'] / pip:.1f} نقطة | R:R = 1:2\n"
        f"الحجم المقترح: {lots_line}\n"
        f"━━━━━━━━━━━━\n"
        f"النموذج: {sig['setup']} | التقييم: {sig['score']}/100\n"
        f"{sig['detail']}\n"
        f"الجلسة: {sig['session']}\n"
        f"⏳ تُلغى إن لم تُفعَّل خلال {PENDING_EXPIRY_MIN} دقيقة، أو لمس السعر SL قبل التفعيل، أو انتهت الجلسة."
    )


def kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 الأسعار الحالية", callback_data="prices"),
         InlineKeyboardButton("📌 الصفقة الحالية", callback_data="signal")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
         InlineKeyboardButton("🕐 الجلسات", callback_data="session")],
    ])


def authorized(chat_id):
    return (not CHAT_IDS) or chat_id in CHAT_IDS


def recipients():
    return list(CHAT_IDS) if CHAT_IDS else state["chats"]


async def broadcast(app, text):
    for cid in recipients():
        try:
            await app.bot.send_message(cid, text, parse_mode=ParseMode.HTML, reply_markup=kb())
        except Exception as e:
            log.warning("send to %s failed: %s", cid, e)


async def render(app, kind):
    http = app.bot_data["http"]
    if kind == "prices":
        try:
            pr = await get_prices(http, list(SYMBOLS))
        except Exception as e:
            return f"تعذر جلب الأسعار: {e}"
        lines = ["💰 <b>الأسعار الحالية (CFD)</b>"]
        for s in SYMBOLS:
            if s in pr:
                b, a, _ = pr[s]
                lines.append(f"<b>{s}</b>  Bid <code>{fmt(s, b)}</code> | Ask <code>{fmt(s, a)}</code> | سبريد {fmt(s, a - b)}")
        lines.append(f"\n🕐 {now_utc().strftime('%H:%M:%S')} UTC")
        return "\n".join(lines)
    if kind == "signal":
        sig = state["signal"]
        if not sig:
            ss = session_info()
            return ("🔎 لا توجد صفقة نشطة حالياً — البوت يمسح السوق."
                    + (f"\nالجلسة الحالية: {ss[0]}" if ss else "\nخارج جلستي لندن ونيويورك."))
        try:
            pr = await get_prices(http, [sig["symbol"]])
            b, a, _ = pr[sig["symbol"]]
        except Exception:
            b = a = sig["entry"]
        st = "⏳ أمر معلق (لم يُفعَّل)" if sig["status"] == "PENDING" else "✅ مُفعَّلة"
        return signal_text(sig, b, a, title=f"📌 الصفقة الحالية — {st}")
    if kind == "stats":
        s = state["stats"]
        n = s["win"] + s["loss"]
        wr = (s["win"] / n * 100) if n else 0
        return (f"📊 <b>الإحصائيات</b>\n✅ رابحة: {s['win']} | ❌ خاسرة: {s['loss']} | ⚪ تعادل: {s['be']} | 🚫 ملغاة: {s['cancel']}\n"
                f"نسبة النجاح: {wr:.1f}% (من {n} صفقة مُفعَّلة)\n"
                f"صافي النتيجة: {s['r']:+.1f}R\n"
                f"اليوم: {state['day_signals']}/{MAX_SIGNALS_DAY} إشارات | {state['day_losses']}/{MAX_LOSSES_DAY} خسائر")
    ss = session_info()
    return (f"🕐 الجلسة الحالية: <b>{ss[0]}</b> (متبقي {ss[1]} دقيقة)" if ss
            else "🕐 خارج جلستي لندن ونيويورك — لا إشارات الآن.")


# ───────────── المهام الدورية ─────────────
async def scan_job(ctx: ContextTypes.DEFAULT_TYPE):
    async with LOCK:
        reset_day()
        if state["signal"]:
            return  # لا إشارة جديدة قبل انتهاء السابقة
        ss = session_info()
        if not ss or ss[1] < 60:
            return
        if state["day_signals"] >= MAX_SIGNALS_DAY or state["day_losses"] >= MAX_LOSSES_DAY:
            return
        http = ctx.application.bot_data["http"]
        now = time.time()
        syms = [s for s in SYMBOLS if state["cooldown"].get(s, 0) < now]
        if not syms:
            return
        try:
            prices = await get_prices(http, syms)
        except Exception as e:
            log.warning("prices: %s", e)
            return
        cands = []
        for s in syms:
            if s not in prices or not prices[s][2]:
                continue
            try:
                inst = SYMBOLS[s]["inst"]
                m15 = await cached(http, inst, "M15", 200, 25)
                h1 = await cached(http, inst, "H1", 200, 600)
                d1 = await cached(http, inst, "D", 5, 1800)
                cands += analyze(s, m15, h1, d1, prices[s][0], prices[s][1])
            except Exception as e:
                log.warning("analyze %s: %s", s, e)
        if not cands:
            return
        best = max(cands, key=lambda x: x["score"])
        if best["score"] < MIN_SCORE:
            return
        best.update(id=state["next_id"], status="PENDING", created=time.time(), session=ss[0], be=False)
        state["next_id"] += 1
        state["day_signals"] += 1
        state["signal"] = best
        save_state()
        b, a, _ = prices[best["symbol"]]
        await broadcast(ctx.application, signal_text(best, b, a))
        log.info("signal %s %s score=%s", best["symbol"], best["side"], best["score"])


async def finish(app, sig, result, why=""):
    s = state["stats"]
    sym = sig["symbol"]
    if result == "WIN":
        s["win"] += 1; s["r"] += RR
        msg = f"🏆 <b>#{sig['id']} {sym}</b> — تحقق الهدف  +{RR:g}R"
    elif result == "LOSS":
        s["loss"] += 1; s["r"] -= 1; state["day_losses"] += 1
        msg = f"❌ <b>#{sig['id']} {sym}</b> — ضرب وقف الخسارة  −1R"
    elif result == "BE":
        s["be"] += 1
        msg = f"⚪ <b>#{sig['id']} {sym}</b> — أُغلقت عند نقطة الدخول  0R"
    else:
        s["cancel"] += 1
        msg = f"🚫 <b>#{sig['id']} {sym}</b> — أُلغي الأمر المعلق\nالسبب: {why}\n(لا تنفّذه، ولا تُبقِه في المنصة)"
    state["cooldown"][sym] = time.time() + COOLDOWN_MIN * 60
    state["signal"] = None
    save_state()
    await broadcast(app, msg + "\n\n🔎 البوت يبحث عن الفرصة التالية…")


async def monitor_job(ctx: ContextTypes.DEFAULT_TYPE):
    async with LOCK:
        sig = state["signal"]
        if not sig:
            return
        app = ctx.application
        try:
            pr = await get_prices(app.bot_data["http"], [sig["symbol"]])
            bid, ask, _ = pr[sig["symbol"]]
        except Exception as e:
            log.warning("monitor: %s", e)
            return
        buy = sig["side"] == "BUY"
        sym = sig["symbol"]
        if sig["status"] == "PENDING":
            trig = ask >= sig["entry"] if buy else bid <= sig["entry"]
            sl_hit = bid <= sig["sl"] if buy else ask >= sig["sl"]
            if trig:
                sig["status"] = "ACTIVE"
                save_state()
    
