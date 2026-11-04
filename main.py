import os
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import uvicorn

from strategy import GoldStrategy, SignalBook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("AL-GHRAM")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
FEED_SECRET = os.getenv("FEED_SECRET", "").strip()
PORT = int(os.getenv("PORT", "10000"))

ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

strategy = GoldStrategy()
book = SignalBook(max_daily_signals=4)

telegram_app = None
subscribers = set(ADMIN_IDS)


def load_subscribers():
    global subscribers

    try:
        with open("subscribers.json", "r") as f:
            subscribers.update(int(x) for x in json.load(f))
    except Exception:
        pass


def save_subscribers():
    try:
        with open("subscribers.json", "w") as f:
            json.dump(list(subscribers), f)
    except Exception:
        log.exception("Subscriber save error")


def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 حالة النظام",
                callback_data="status"
            )
        ],
        [
            InlineKeyboardButton(
                "📈 الاستراتيجية",
                callback_data="rules"
            )
        ],
        [
            InlineKeyboardButton(
                "🔔 الاشتراك",
                callback_data="subscribe"
            )
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    subscribers.add(user_id)
    save_subscribers()

    await update.message.reply_text(
        "👑 AL-GHRAM AI TRADING\n\n"
        "Gold CFD | xChief Classic+\n"
        "نظام تحليل الذهب الذكي\n\n"
        "مصدر الأسعار: حساب MT5 الخاص بك.\n\n"
        "⚠️ هذه النسخة تجريبية وترسل إشارات فقط.",
        reply_markup=menu()
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    active = book.active

    if active:
        state = (
            f"{active['order_type']}\n"
            f"Entry: {active['entry']}\n"
            f"Status: {active['status']}"
        )
    else:
        state = "لا توجد إشارة نشطة"

    await update.message.reply_text(
        "📊 AL-GHRAM STATUS\n\n"
        f"Symbol: {book.symbol}\n"
        f"Signals: {book.daily_count}/4\n\n"
        f"{state}"
    )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🧠 AL-GHRAM LQG ENGINE\n\n"
        "1. Liquidity Mapping\n"
        "2. Volume Intelligence\n"
        "3. Market Structure\n"
        "4. Support & Resistance\n"
        "5. ATR Volatility Filter\n"
        "6. London Session\n"
        "7. New York Session\n\n"
        "Risk Reward: 1:2\n"
        "Maximum Signals: 4\n"
        "Active Signals: 1"
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    subscribers.add(update.effective_user.id)
    save_subscribers()

    await update.message.reply_text(
        "✅ تم تفعيل الاشتراك في التنبيهات."
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "status":

        active = book.active

        state = "لا توجد إشارة" if not active else active["status"]

        await query.edit_message_text(
            f"📊 حالة النظام\n\n"
            f"الحالة: {state}\n"
            f"الإشارات اليومية: {book.daily_count}/4"
        )

    elif query.data == "rules":

        await query.edit_message_text(
            "AL-GHRAM LQG\n\n"
            "Liquidity + Volume + Structure\n"
            "BUY STOP / SELL STOP\n"
            "Risk Reward 1:2"
        )

    elif query.data == "subscribe":

        subscribers.add(query.from_user.id)
        save_subscribers()

        await query.edit_message_text(
            "✅ تم الاشتراك بنجاح."
        )


async def broadcast(message):

    if telegram_app is None:
        return

    for user_id in list(subscribers):

        try:
            await telegram_app.bot.send_message(
                chat_id=user_id,
                text=message
            )

        except Exception:
            log.exception("Telegram send error")


class Bar(BaseModel):

    time: str
    open: float
    high: float
    low: float
    close: float
    tick_volume: float = Field(ge=0)


class FeedPayload(BaseModel):

    symbol: str
    timeframe: str = "M5"
    digits: int = Field(default=2, ge=0, le=8)

    bid: float = Field(gt=0)
    ask: float = Field(gt=0)

    bars: list[Bar] = Field(
        min_length=40,
        max_length=500
    )


@asynccontextmanager
async def lifespan(app: FastAPI):

    global telegram_app

    if not BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    if not FEED_SECRET:
        raise RuntimeError("Missing FEED_SECRET")

    load_subscribers()

    telegram_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("rules", rules))
    telegram_app.add_handler(CommandHandler("subscribe", subscribe))

    telegram_app.add_handler(
        CallbackQueryHandler(buttons)
    )

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(
        drop_pending_updates=True
    )

    log.info("AL-GHRAM started")

    yield

    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()


api = FastAPI(
    title="AL-GHRAM AI TRADING",
    lifespan=lifespan
)


@api.get("/")
async def home():

    return {
        "name": "AL-GHRAM AI TRADING",
        "status": "online",
        "mode": "signals_only"
    }


@api.get("/health")
async def health():

    return {
        "ok": True,
        "telegram": telegram_app is not None,
        "market": "waiting for MT5"
    }


@api.post("/feed/bars")
async def receive_bars(
    payload: FeedPayload,
    x_feed_secret: str | None = Header(default=None)
):

    if x_feed_secret != FEED_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid secret"
        )

    symbol = payload.symbol.upper().strip()

    if "XAUUSD" not in symbol:
        raise HTTPException(
            status_code=400,
            detail="Only XAUUSD CFD is allowed"
        )

    if payload.ask < payload.bid:
        raise HTTPException(
            status_code=400,
            detail="Invalid Bid/Ask"
        )

    if payload.timeframe.upper() != "M5":
        raise HTTPException(
            status_code=400,
            detail="M5 only"
        )

    bars = [
        bar.model_dump()
        for bar in payload.bars
    ]

    book.symbol = symbol

    events = book.update_market(
        bars=bars,
        bid=payload.bid,
        ask=payload.ask,
        strategy=strategy,
        symbol=symbol,
        bar_time=bars[-1]["time"],
        digits=payload.digits
    )

    for event in events:
        await broadcast(event)

    return {
        "ok": True,
        "symbol": symbol,
        "events": len(events),
        "active": book.active
    }


if __name__ == "__main__":

    uvicorn.run(
        api,
        host="0.0.0.0",
        port=PORT
)            if not t:
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
    
