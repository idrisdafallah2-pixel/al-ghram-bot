import os
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from strategy import GoldStrategy, SignalBook


# -------------------- SETTINGS --------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("AL-GHRAM")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
FEED_SECRET = os.getenv("FEED_SECRET", "").strip()
PORT = int(os.getenv("PORT", "10000"))
SUBSCRIBERS_PATH = Path(os.getenv("SUBSCRIBERS_FILE", "subscribers.json"))

ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}

strategy = GoldStrategy()
signal_book = SignalBook(max_daily_signals=4)
subscribers = set(ADMIN_IDS)
telegram_app: Optional[Application] = None


# -------------------- SUBSCRIBERS --------------------

def load_subscribers():
    try:
        if SUBSCRIBERS_PATH.exists():
            data = json.loads(SUBSCRIBERS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    try:
                        subscribers.add(int(item))
                    except (TypeError, ValueError):
                        continue
    except Exception:
        logger.exception("Could not load subscribers")


def save_subscribers():
    try:
        SUBSCRIBERS_PATH.write_text(
            json.dumps(sorted(subscribers)),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Could not save subscribers")


# -------------------- TELEGRAM UI --------------------

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 حالة النظام", callback_data="status")],
        [InlineKeyboardButton("📈 الاستراتيجية", callback_data="rules")],
        [InlineKeyboardButton("🔔 تفعيل التنبيهات", callback_data="subscribe")],
    ])


def status_text():
    active = signal_book.active

    if active:
        active_text = (
            f"النوع: {active.get('order_type', '-')}\n"
            f"الدخول: {active.get('entry', '-')}\n"
            f"الحالة: {active.get('status', '-')}"
        )
    else:
        active_text = "لا توجد إشارة نشطة."

    return (
        "📊 AL-GHRAM STATUS\n\n"
        f"الرمز: {signal_book.symbol or 'بانتظار بيانات MT5'}\n"
        f"الإشارات اليومية: {signal_book.daily_count}/4\n\n"
        f"{active_text}\n\n"
        "⚠️ الإشارات نظرية ولا تنفذ صفقات لدى الوسيط."
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user is None or update.effective_message is None:
        return

    subscribers.add(user.id)
    save_subscribers()

    await update.effective_message.reply_text(
        "👑 AL-GHRAM AI TRADING\n\n"
        "الأداة مخصصة لتحليل XAUUSD CFD على إطار M5.\n"
        "مصدر الأسعار: جسر MT5 الخاص بك.\n"
        "الجلسات: لندن ونيويورك.\n"
        "نوع الإشارات: BUY STOP / SELL STOP.\n"
        "نسبة العائد إلى المخاطرة المستهدفة: 1:2.\n\n"
        "⚠️ هذه النسخة ترسل إشارات نظرية فقط، ولا تفتح صفقات.",
        reply_markup=main_menu(),
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message:
        await update.effective_message.reply_text(status_text())


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message:
        await update.effective_message.reply_text(
            "📈 AL-GHRAM STRATEGY\n\n"
            "• XAUUSD CFD فقط\n"
            "• إطار M5\n"
            "• جلسة لندن ونيويورك\n"
            "• تحليل السيولة ومناطق السحب\n"
            "• حجم التداول Tick Volume\n"
            "• هيكل السوق والاختراق\n"
            "• فلتر ATR والسبريد\n"
            "• BUY STOP / SELL STOP\n"
            "• Risk:Reward = 1:2\n"
            "• حد أقصى 4 إشارات يومياً\n\n"
            "⚠️ النتائج تحتاج اختباراً تاريخياً وتجريبياً.",
        )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user is None or update.effective_message is None:
        return

    subscribers.add(user.id)
    save_subscribers()

    await update.effective_message.reply_text(
        "✅ تم تفعيل استقبال التنبيهات."
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    if query.data == "status":
        await query.edit_message_text(
            status_text(),
            reply_markup=main_menu(),
        )

    elif query.data == "rules":
        await query.edit_message_text(
            "📈 XAUUSD CFD | M5\n"
            "السيولة + Tick Volume + هيكل السوق + ATR\n"
            "جلسات لندن ونيويورك\n"
            "BUY STOP / SELL STOP | RR 1:2\n\n"
            "⚠️ إشارات نظرية فقط.",
            reply_markup=main_menu(),
        )

    elif query.data == "subscribe":
        subscribers.add(query.from_user.id)
        save_subscribers()

        await query.edit_message_text(
            "✅ تم تفعيل استقبال التنبيهات.",
            reply_markup=main_menu(),
        )


async def send_to_subscribers(message: str):
    if telegram_app is None:
        logger.warning("Telegram is not ready; notification was skipped")
        return

    for chat_id in list(subscribers):
        try:
            await telegram_app.bot.send_message(
                chat_id=chat_id,
                text=message,
            )
        except Exception:
            logger.exception(
                "Could not send Telegram message to %s",
                chat_id,
            )


# -------------------- MT5 DATA MODELS --------------------

class Candle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    tick_volume: float = Field(ge=0)


class MarketFeed(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    timeframe: str = "M5"
    digits: int = Field(default=2, ge=0, le=8)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bars: list[Candle] = Field(min_length=40, max_length=500)


# -------------------- APPLICATION LIFECYCLE --------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    if not BOT_TOKEN:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN environment variable"
        )

    if not FEED_SECRET:
        raise RuntimeError(
            "Missing FEED_SECRET environment variable"
        )

    load_subscribers()

    telegram_app = Application.builder().token(BOT_TOKEN).build()

    telegram_app.add_handler(
        CommandHandler("start", start_command)
    )
    telegram_app.add_handler(
        CommandHandler("status", status_command)
    )
    telegram_app.add_handler(
        CommandHandler("rules", rules_command)
    )
    telegram_app.add_handler(
        CommandHandler("subscribe", subscribe_command)
    )
    telegram_app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    await telegram_app.initialize()
    await telegram_app.start()

    if telegram_app.updater is None:
        raise RuntimeError(
            "Telegram updater could not be initialized"
        )

    await telegram_app.updater.start_polling(
        drop_pending_updates=True
    )

    logger.info("AL-GHRAM service started")

    try:
        yield

    finally:
        if telegram_app is not None:
            if telegram_app.updater is not None:
                await telegram_app.updater.stop()

            await telegram_app.stop()
            await telegram_app.shutdown()
            telegram_app = None


# -------------------- FASTAPI --------------------

api = FastAPI(
    title="AL-GHRAM AI TRADING",
    version="1.1.0",
    lifespan=lifespan,
)


@api.get("/")
async def home():
    return {
        "name": "AL-GHRAM AI TRADING",
        "status": "online",
        "mode": "signals_only",
    }


@api.get("/health")
async def health():
    return {
        "ok": True,
        "telegram_ready": telegram_app is not None,
        "market_data": "waiting_for_mt5_feed",
    }


@api.post("/feed/bars")
async def receive_market_feed(
    payload: MarketFeed,
    x_feed_secret: str | None = Header(default=None),
):
    if not FEED_SECRET or x_feed_secret != FEED_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid feed secret",
        )

    symbol = payload.symbol.strip().upper()

    if not symbol.startswith("XAUUSD"):
        raise HTTPException(
            status_code=400,
            detail="Only XAUUSD CFD symbols are accepted",
        )

    if payload.timeframe.strip().upper() != "M5":
        raise HTTPException(
            status_code=400,
            detail="M5 timeframe is required",
        )

    if payload.ask < payload.bid:
        raise HTTPException(
            status_code=400,
            detail="Ask must be greater than or equal to Bid",
        )

    bars = [
        candle.model_dump()
        for candle in payload.bars
    ]

    for candle in bars:
        if candle["high"] < max(
            candle["open"],
            candle["close"],
            candle["low"],
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid candle high",
            )

        if candle["low"] > min(
            candle["open"],
            candle["close"],
            candle["high"],
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid candle low",
            )

    signal_book.symbol = symbol

    events = signal_book.update_market(
        bars=bars,
        bid=payload.bid,
        ask=payload.ask,
        strategy=strategy,
        symbol=symbol,
        bar_time=bars[-1]["time"],
        digits=payload.digits,
    )

    for event in events:
        await send_to_subscribers(event)

    return {
        "ok": True,
        "symbol": symbol,
        "received_candles": len(bars),
        "new_events": len(events),
        "active_signal": signal_book.active,
    }


# -------------------- START SERVER --------------------

if __name__ == "__main__":
    uvicorn.run(
        api,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )        status_code=422,
                detail=f"Invalid candle low at {index}",
            )

    book.symbol = symbol

    try:

        events = book.update_market(
            bars=bars,
            bid=payload.bid,
            ask=payload.ask,
            strategy=strategy,
            symbol=symbol,
            bar_time=bars[-1]["time"],
            digits=payload.digits,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        ZeroDivisionError,
    ):

        log.exception("Strategy processing failed")

        raise HTTPException(
            status_code=422,
            detail="Market data processing failed",
        )

    for event in events:

        await broadcast(event)

    return {
        "ok": True,
        "symbol": symbol,
        "timeframe": payload.timeframe.upper(),
        "events": len(events),
        "active": book.active,
        "daily_signals": book.daily_count,
    }


# =====================================
# RUN SERVER
# =====================================

if __name__ == "__main__":

    uvicorn.run(
        api,
        host="0.0.0.0",
        port=PORT,
            )e']} STOP</b>\n"
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
    
