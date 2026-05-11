"""
Spot Testnet entry strategy — scoring + gates (BUY only).

Uses Testnet public klines; does not place orders or touch portfolio math.
"""

from __future__ import annotations

import logging
from typing import Any

from app.demo_bot_constants import (
    TESTNET_STRATEGY_ATR_PERIOD,
    TESTNET_STRATEGY_ATR_PCT_MAX,
    TESTNET_STRATEGY_ATR_PCT_MIN,
    TESTNET_STRATEGY_EMA_FAST,
    TESTNET_STRATEGY_EMA_SLOW,
    TESTNET_STRATEGY_KLINE_INTERVAL,
    TESTNET_STRATEGY_KLINE_LIMIT,
    TESTNET_STRATEGY_MIN_CONFIDENCE,
    TESTNET_STRATEGY_MIN_CONFIDENCE_AFTER_LOSS,
    TESTNET_STRATEGY_MIN_RISK_SCORE,
    TESTNET_STRATEGY_MIN_TOTAL_SCORE,
    TESTNET_STRATEGY_RSI_PERIOD,
)
from app.services.binance_testnet_service import BinanceTestnetService
from app.services.bot_state_service import BotStateService

logger = logging.getLogger(__name__)


def _ema_last(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    ema = sum(closes[:period]) / period
    k = 2.0 / (period + 1.0)
    for c in closes[period:]:
        ema = c * k + ema * (1.0 - k)
    return ema


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _true_range(h: float, l: float, prev_c: float) -> float:
    return max(h - l, abs(h - prev_c), abs(l - prev_c))


def _atr_pct(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int,
) -> float | None:
    if len(closes) < period + 2:
        return None
    trs: list[float] = []
    for i in range(1, len(closes)):
        trs.append(_true_range(highs[i], lows[i], closes[i - 1]))
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for t in trs[period:]:
        atr = (atr * (period - 1) + t) / period
    last = closes[-1]
    if last <= 0:
        return None
    return atr / last


def _trend_score_and_veto(
    closes: list[float],
    fast: int,
    slow: int,
) -> tuple[float, bool, list[str]]:
    reasons: list[str] = []
    if len(closes) < slow + 2:
        return 0.0, True, ["Insufficient klines for EMA."]
    f = _ema_last(closes, fast)
    s = _ema_last(closes, slow)
    if f is None or s is None:
        return 0.0, True, ["EMA could not be computed."]
    if f > s:
        sep = abs(f - s) / s if s > 0 else 0.0
        score = min(100.0, 70.0 + min(30.0, sep * 5000.0))
        reasons.append(
            f"Trend: fast EMA({fast}) above slow EMA({slow}) (bullish, separation={sep:.5f}).",
        )
        return score, False, reasons
    reasons.append(
        f"Trend: fast EMA({fast})<=slow EMA({slow}) (no BUY; fast={f:.6f} slow={s:.6f}).",
    )
    return 0.0, True, reasons


def _momentum_score_and_veto(rsi: float | None) -> tuple[float, bool, list[str]]:
    if rsi is None:
        return 0.0, True, ["RSI unavailable."]
    reasons: list[str] = [f"RSI(14)={rsi:.2f}."]
    if rsi >= 72.0:
        reasons.append("Momentum: overbought — skip BUY.")
        return 15.0, True, reasons
    if rsi <= 28.0:
        reasons.append("Momentum: extremely weak — skip BUY.")
        return 15.0, True, reasons
    if 40.0 <= rsi <= 60.0:
        return 92.0, False, reasons + ["Momentum: neutral band (healthy)."]
    if 30.0 <= rsi < 40.0:
        return 78.0, False, reasons + ["Momentum: recovering from weak (not overbought)."]
    if 60.0 < rsi < 72.0:
        return 58.0, False, reasons + ["Momentum: warming (watch overbought)."]
    if 28.0 < rsi < 30.0:
        return 55.0, False, reasons + ["Momentum: fragile lift."]
    return 65.0, False, reasons + ["Momentum: mid-range."]


def _volatility_score_and_veto(atr_pct: float | None) -> tuple[float, bool, list[str]]:
    if atr_pct is None:
        return 0.0, True, ["ATR% unavailable."]
    reasons = [f"ATR%={atr_pct:.6f}."]
    if atr_pct > TESTNET_STRATEGY_ATR_PCT_MAX:
        reasons.append("Volatility: too high — skip.")
        return 10.0, True, reasons
    if atr_pct < TESTNET_STRATEGY_ATR_PCT_MIN:
        reasons.append("Volatility: too low (chop/stale) — skip.")
        return 10.0, True, reasons
    mid = (TESTNET_STRATEGY_ATR_PCT_MIN + TESTNET_STRATEGY_ATR_PCT_MAX) / 2.0
    span = TESTNET_STRATEGY_ATR_PCT_MAX - TESTNET_STRATEGY_ATR_PCT_MIN
    dist = 1.0 - min(1.0, abs(atr_pct - mid) / (span / 2.0))
    score = 55.0 + 45.0 * dist
    reasons.append("Volatility: within tradable band.")
    return score, False, reasons


def build_testnet_entry_packet(
    *,
    symbol: str,
    binance: BinanceTestnetService,
    state: BotStateService,
    confidence: float,
    risk_score: float,
) -> dict[str, Any]:
    """
    Returns a dict stored on ``DecisionModel.testnet_entry`` with scores, reasons, and ``passed``.
    """
    sym = symbol.strip().upper()
    all_reasons: list[str] = []

    def _fail(skip: str, **scores: Any) -> dict[str, Any]:
        pkt = {
            "passed": False,
            "verdict": "SKIP",
            "skip_reason": skip,
            "reasons": list(all_reasons),
            "reasons_text": "; ".join(all_reasons) if all_reasons else skip,
            "trend_score": scores.get("trend_score"),
            "momentum_score": scores.get("momentum_score"),
            "volatility_score": scores.get("volatility_score"),
            "total_score": scores.get("total_score"),
            "risk_score": risk_score,
            "confidence": confidence,
        }
        _log_packet(sym, pkt)
        return pkt

    block = state.testnet_buy_blocked_reason(sym)
    if block:
        all_reasons.append(block)
        return _fail(block)

    # Risk / confidence gates (agent risk_score: higher = safer in this demo stack).
    if risk_score < TESTNET_STRATEGY_MIN_RISK_SCORE:
        msg = (
            f"Risk gate: risk_score {risk_score:.1f} < required "
            f"{TESTNET_STRATEGY_MIN_RISK_SCORE:.0f} (higher is safer in demo agents)."
        )
        all_reasons.append(msg)
        return _fail(msg, trend_score=None, momentum_score=None, volatility_score=None, total_score=None)

    min_conf = (
        TESTNET_STRATEGY_MIN_CONFIDENCE_AFTER_LOSS
        if state.testnet_last_closed_trade_was_loss(sym)
        else TESTNET_STRATEGY_MIN_CONFIDENCE
    )
    if confidence < min_conf:
        msg = f"Confidence gate: need {min_conf:.0f}, got {confidence:.1f}."
        all_reasons.append(msg)
        return _fail(msg, trend_score=None, momentum_score=None, volatility_score=None, total_score=None)

    try:
        raw = binance.get_klines_public(
            sym,
            interval=TESTNET_STRATEGY_KLINE_INTERVAL,
            limit=TESTNET_STRATEGY_KLINE_LIMIT,
        )
    except Exception as exc:
        msg = f"Klines fetch failed: {exc}"
        all_reasons.append(msg)
        return _fail(msg)

    if not raw or not isinstance(raw[0], list) or len(raw[0]) < 6:
        all_reasons.append("Klines empty or malformed.")
        return _fail("Klines empty or malformed.")

    highs = [float(k[2]) for k in raw]
    lows = [float(k[3]) for k in raw]
    closes = [float(k[4]) for k in raw]

    trend_s, trend_veto, tr_r = _trend_score_and_veto(
        closes,
        TESTNET_STRATEGY_EMA_FAST,
        TESTNET_STRATEGY_EMA_SLOW,
    )
    all_reasons.extend(tr_r)

    rsi = _rsi(closes, TESTNET_STRATEGY_RSI_PERIOD)
    mom_s, mom_veto, mom_r = _momentum_score_and_veto(rsi)
    all_reasons.extend(mom_r)

    atrp = _atr_pct(highs, lows, closes, TESTNET_STRATEGY_ATR_PERIOD)
    vol_s, vol_veto, vol_r = _volatility_score_and_veto(atrp)
    all_reasons.extend(vol_r)

    if trend_veto or mom_veto or vol_veto:
        total = 0.35 * trend_s + 0.35 * mom_s + 0.30 * vol_s
        msg = "Signal veto (trend/momentum/volatility) — no BUY."
        all_reasons.append(msg)
        return _fail(
            msg,
            trend_score=round(trend_s, 2),
            momentum_score=round(mom_s, 2),
            volatility_score=round(vol_s, 2),
            total_score=round(total, 2),
        )

    total = 0.35 * trend_s + 0.35 * mom_s + 0.30 * vol_s
    total_r = round(min(100.0, total), 2)

    if total_r < TESTNET_STRATEGY_MIN_TOTAL_SCORE:
        msg = (
            f"Score gate: total {total_r:.1f} < required "
            f"{TESTNET_STRATEGY_MIN_TOTAL_SCORE:.0f}."
        )
        all_reasons.append(msg)
        return _fail(
            msg,
            trend_score=round(trend_s, 2),
            momentum_score=round(mom_s, 2),
            volatility_score=round(vol_s, 2),
            total_score=total_r,
        )

    all_reasons.append(
        f"OPEN: total_score={total_r:.1f} >= {TESTNET_STRATEGY_MIN_TOTAL_SCORE:.0f} "
        "and all vetoes cleared.",
    )
    pkt = {
        "passed": True,
        "verdict": "OPEN",
        "skip_reason": None,
        "trend_score": round(trend_s, 2),
        "momentum_score": round(mom_s, 2),
        "volatility_score": round(vol_s, 2),
        "total_score": total_r,
        "risk_score": risk_score,
        "confidence": confidence,
        "rsi": None if rsi is None else round(rsi, 4),
        "atr_pct": None if atrp is None else round(atrp, 8),
        "reasons": list(all_reasons),
        "reasons_text": "; ".join(all_reasons),
    }
    _log_packet(sym, pkt)
    return pkt


def _log_packet(sym: str, pkt: dict[str, Any]) -> None:
    logger.info(
        "Testnet strategy %s symbol=%s trend_score=%s momentum_score=%s volatility_score=%s "
        "total_score=%s risk_score=%s confidence=%s verdict=%s reasons=%s",
        "entry",
        sym,
        pkt.get("trend_score"),
        pkt.get("momentum_score"),
        pkt.get("volatility_score"),
        pkt.get("total_score"),
        pkt.get("risk_score"),
        pkt.get("confidence"),
        pkt.get("verdict"),
        pkt.get("reasons_text", ""),
    )
