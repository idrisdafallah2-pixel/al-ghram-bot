from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statistics import median


def parse_time(value):

    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def in_allowed_session(dt):

    london = dt.astimezone(
        ZoneInfo("Europe/London")
    )

    ny = dt.astimezone(
        ZoneInfo("America/New_York")
    )

    london_ok = 7 <= london.hour < 11
    ny_ok = 8 <= ny.hour < 12

    return london_ok or ny_ok


def atr(bars, period=14):

    rows = bars[-(period + 1):]

    trs = []

    for i in range(1, len(rows)):

        cur = rows[i]
        prev = rows[i - 1]

        tr = max(
            cur["high"] - cur["low"],
            abs(cur["high"] - prev["close"]),
            abs(cur["low"] - prev["close"])
        )

        trs.append(tr)

    return sum(trs) / len(trs) if trs else 0


class GoldStrategy:

    def evaluate(self, bars, bid, ask, digits=2):

        if len(bars) < 40:
            return None

        current = bars[-1]

        dt = parse_time(current["time"])

        if not in_allowed_session(dt):
            return None

        volatility = atr(bars)

        if volatility <= 0:
            return None

        spread = ask - bid

        if spread > volatility * 0.12:
            return None

        recent = bars[-11:-1]

        vol_base = median([
            x["tick_volume"]
            for x in bars[-31:-1]
        ])

        if vol_base <= 0:
            return None

        volume_ratio = (
            current["tick_volume"] / vol_base
        )

        candle_range = max(
            current["high"] - current["low"],
            0.0000001
        )

        body_ratio = (
            abs(current["close"] - current["open"])
            / candle_range
        )

        impulse = (
            body_ratio >= 0.58
            and candle_range >= volatility * 0.75
        )

        high_break = (
            current["close"]
            > max(x["high"] for x in recent)
        )

        low_break = (
            current["close"]
            < min(x["low"] for x in recent)
        )

        lookback = bars[-29:-9]

        local_high = max(
            x["high"] for x in lookback
        )

        local_low = min(
            x["low"] for x in lookback
        )

        sweep_low = any(
            x["low"] < local_low
            and x["close"] > local_low
            for x in bars[-9:-1]
        )

        sweep_high = any(
            x["high"] > local_high
            and x["close"] < local_high
            for x in bars[-9:-1]
        )

        midpoint = (
            local_high + local_low
        ) / 2

        bullish = current["close"] > midpoint
        bearish = current["close"] < midpoint

        volume_ok = volume_ratio >= 1.30

        candidates = []

        if (
            sweep_low
            and high_break
            and bullish
            and volume_ok
            and impulse
        ):

            candidates.append(
                (
                    "BUY",
                    100,
                    local_low,
                    current["high"]
                )
            )

        if (
            sweep_high
            and low_break
            and bearish
            and volume_ok
            and impulse
        ):

            candidates.append(
                (
                    "SELL",
                    100,
                    local_high,
                    current["low"]
                )
            )

        if not candidates:
            return None

        side, score, swept_level, trigger = candidates[0]

        buffer = max(
            spread * 2,
            volatility * 0.08
        )

        if side == "BUY":

            entry = max(
                trigger + buffer,
                ask + buffer
            )

            sl = swept_level - max(
                spread,
                volatility * 0.10
            )

            risk = entry - sl

            if (
                risk <= max(spread * 3, volatility * 0.25)
                or risk > volatility * 3
            ):
                return None

            tp = entry + 2 * risk

            order_type = "BUY STOP"

        else:

            entry = min(
                trigger - buffer,
                bid - buffer
            )

            sl = swept_level + max(
                spread,
                volatility * 0.10
            )

            risk = sl - entry

            if (
                risk <= max(spread * 3, volatility * 0.25)
                or risk > volatility * 3
            ):
                return None

            tp = entry - 2 * risk

            order_type = "SELL STOP"

        return {
            "side": side,
            "order_type": order_type,
            "entry": round(entry, digits),
            "sl": round(sl, digits),
            "tp": round(tp, digits),
            "risk_distance": round(risk, digits),
            "rr": "1:2",
            "score": score,
            "volume_ratio": round(volume_ratio, 2),
            "spread": round(spread, digits),
            "atr": round(volatility, digits),
            "invalidation": round(sl, digits),
            "created_at": dt.isoformat(),
            "expires_minutes": 45
        }


class SignalBook:

    def __init__(self, max_daily_signals=4):

        self.max_daily_signals = max_daily_signals

        self.active = None

        self.daily_count = 0

        self.daily_key = None

        self.symbol = None

        self.last_bar_time = None

    def update_market(
        self,
        bars,
        bid,
        ask,
        strategy,
        symbol,
        bar_time,
        digits=2
    ):

        events = []

        current = bars[-1]

        dt = parse_time(current["time"])

        day_key = dt.strftime("%Y-%m-%d")

        if self.daily_key != day_key:

            self.daily_key = day_key
            self.daily_count = 0

        if self.last_bar_time == bar_time:
            return events

        self.last_bar_time = bar_time

        if self.active:

            signal = self.active

            age = (
                dt - parse_time(signal["created_at"])
            ).total_seconds() / 60

            side = signal["side"]

            if signal["status"] == "PENDING":

                invalid = (
                    side == "BUY"
                    and current["close"] <= signal["invalidation"]
                ) or (
                    side == "SELL"
                    and current["close"] >= signal["invalidation"]
                )

                touched = (
                    side == "BUY"
                    and current["high"] >= signal["entry"]
                ) or (
                    side == "SELL"
                    and current["low"] <= signal["entry"]
                )

                if invalid:

                    events.append(
                        "❌ تم إلغاء الإشارة بسبب تغير هيكل السعر."
                    )

                    self.active = None

                elif touched:

                    signal["status"] = "TRIGGERED"

                    signal["triggered_at"] = dt.isoformat()

                    events.append(
                        "🟢 وصل السعر إلى مستوى الدخول النظري.\n"
                        "هذا ليس تأكيداً لتنفيذ الأمر لدى الوسيط."
                    )

                elif age >= signal["expires_minutes"]:

                    events.append(
                        "⌛ انتهت صلاحية الإشارة وتم إلغاؤها."
                    )

                    self.active = None

            elif signal["status"] == "TRIGGERED":

                hit_sl = (
                    side == "BUY"
                    and current["low"] <= signal["sl"]
                ) or (
                    side == "SELL"
                    and current["high"] >= signal["sl"]
                )

                hit_tp = (
                    side == "BUY"
                    and current["high"] >= signal["tp"]
                ) or (
                    side == "SELL"
                    and current["low"] <= signal["tp"]
                )

                if hit_sl:

                    events.append(
                        "🔴 وصل السعر إلى وقف الخسارة النظري."
                    )

                    self.active = None

                elif hit_tp:

                    events.append(
                        "🎯 تحقق الهدف النظري 1:2."
                    )

                    self.active = None

                elif age >= 240:

                    events.append(
                        "⌛ انتهت مدة متابعة الإشارة."
                    )

                    self.active = None

        if (
            self.active is None
            and self.daily_count < self.max_daily_signals
        ):

            setup = strategy.evaluate(
                bars,
                bid,
                ask,
                digits
            )

            if setup:

                setup["symbol"] = symbol

                setup["status"] = "PENDING"

                self.active = setup

                self.daily_count += 1

                events.append(
                    "👑 AL-GHRAM AI TRADING\n\n"
                    f"السوق: {symbol} CFD\n"
                    f"النوع: {setup['order_type']}\n"
                    f"الدخول: {setup['entry']}\n"
                    f"وقف الخسارة: {setup['sl']}\n"
                    f"الهدف: {setup['tp']}\n"
                    f"RR: {setup['rr']}\n"
                    f"درجة التوافق: {setup['score']}/100\n"
                    f"حجم التداول: {setup['volume_ratio']}\n"
                    f"السبريد: {setup['spread']}\n"
                    "⚠️ إشارة تجريبية وليست أمراً منفذاً."
                )

        return events
