"""Technical analysis from market bundle (mock TA — deterministic from candles)."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.models.agent_model import AgentResultModel


def _ema_series(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    ema = sum(values[:period]) / period
    k = 2.0 / (period + 1.0)
    for v in values[period:]:
        ema = v * k + ema * (1.0 - k)
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


def _atr_pct(highs: list[float], lows: list[float], closes: list[float], period: int) -> float | None:
    if len(closes) < period + 2:
        return None
    trs: list[float] = []
    for i in range(1, len(closes)):
        h, l, c, pc = highs[i], lows[i], closes[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs[:period]) / period
    for t in trs[period:]:
        atr = (atr * (period - 1) + t) / period
    last = closes[-1]
    if last <= 0:
        return None
    return atr / last


def analyze(
    symbol: str,
    mid: float,
    *,
    market_payload: dict[str, Any] | None = None,
    ai_client: Any | None = None,
) -> AgentResultModel:
    """EMA / RSI / MACD proxy / ATR% / S-R levels -> BUY | SELL | HOLD + reasons."""
    closes: list[float]
    highs: list[float]
    lows: list[float]
    if (
        market_payload
        and isinstance(market_payload.get("closes"), list)
        and len(market_payload["closes"]) >= 20
    ):
        closes = [float(x) for x in market_payload["closes"]]
        highs = [float(x) for x in market_payload.get("highs", market_payload["closes"])]
        lows = [float(x) for x in market_payload.get("lows", market_payload["closes"])]
    else:
        osc = math.sin(mid / 9000.0) * 40.0 + math.cos(mid / 1200.0) * 15.0
        closes = [mid * (1.0 + osc * 1e-5 * i) for i in range(40)]
        highs = [c * 1.001 for c in closes]
        lows = [c * 0.999 for c in closes]

    ema_f = _ema_series(closes, 12)
    ema_s = _ema_series(closes, 26)
    rsi_v = _rsi(closes, 14)
    atrp = _atr_pct(highs, lows, closes, 14)
    macd_raw = None
    if ema_f is not None and ema_s is not None:
        macd_raw = ema_f - ema_s
    window = min(24, len(closes))
    resist = max(highs[-window:])
    support = min(lows[-window:])
    last = closes[-1]
    dist_res = (resist - last) / last if last > 0 else 0.0
    dist_sup = (last - support) / last if last > 0 else 0.0

    reasons: list[str] = []
    bull = 0
    bear = 0
    if ema_f is not None and ema_s is not None:
        if ema_f > ema_s:
            bull += 1
            reasons.append(f"EMA12>EMA26 (bull separation {(ema_f - ema_s) / last * 100:.3f}%).")
        else:
            bear += 1
            reasons.append("EMA12<=EMA26 (bearish / no uptrend).")
    if rsi_v is not None:
        reasons.append(f"RSI14={rsi_v:.1f}.")
        if rsi_v >= 70:
            bear += 1
            reasons.append("RSI stretched — avoid chasing longs.")
        elif rsi_v <= 32:
            bear += 1
            reasons.append("RSI weak — bounce not confirmed.")
        elif 38 <= rsi_v <= 58:
            bull += 1
    if atrp is not None:
        reasons.append(f"ATR%={atrp * 100:.3f} of price.")
        if atrp > 0.02:
            bear += 1
            reasons.append("High ATR% — volatile tape.")
    if dist_res < 0.0015:
        bear += 1
        reasons.append("Price near mock resistance.")
    elif dist_sup < 0.0015:
        bull += 1
        reasons.append("Price near mock support.")

    if bull >= 2 and bear <= 1:
        action = "BUY"
    elif bear >= 2 and bull == 0:
        action = "SELL"
    elif bull > bear:
        action = "BUY"
    elif bear > bull:
        action = "SELL"
    else:
        action = "HOLD"

    combo = (bull - bear) * 12.0 + (macd_raw or 0.0) / (last + 1e-9) * 5000.0
    score = max(-48.0, min(48.0, combo))
    confidence = round(min(72.0 + abs(score) * 0.45 + (bull + bear) * 3.0, 96.0), 2)

    payload: dict[str, Any] = {
        "provider": "mock_rules",
        "ema12": None if ema_f is None else round(ema_f, 8),
        "ema26": None if ema_s is None else round(ema_s, 8),
        "rsi14": None if rsi_v is None else round(rsi_v, 3),
        "macd_estimate": None if macd_raw is None else round(macd_raw, 8),
        "atr_pct": None if atrp is None else round(atrp, 8),
        "support": round(support, 8),
        "resistance": round(resist, 8),
        "trend_strength_score": round(bull - bear, 2),
        "reasons": reasons,
        "action": action,
    }
    if ai_client is not None:
        payload["ai_advice"] = ai_client.analyze_with_ai(
            (
                "Technical interpretation only. Do not execute trades. "
                f"Symbol={symbol}. Mid={mid}. Action from rules={action}. "
                f"Indicators: ema12={payload['ema12']}, ema26={payload['ema26']}, "
                f"rsi14={payload['rsi14']}, macd={payload['macd_estimate']}, "
                f"atr_pct={payload['atr_pct']}, support={payload['support']}, "
                f"resistance={payload['resistance']}. Reasons={reasons}"
            ),
            None,
        )
        payload["ai_provider"] = ai_client.status()

    return AgentResultModel(
        agent_name="Technical Analysis Agent",
        symbol=symbol,
        status="completed",
        score=round(score, 2),
        action=action,
        confidence=confidence,
        explanation=" ".join(reasons) if reasons else "Technical posture neutral.",
        created_at=datetime.now(timezone.utc),
        payload=payload,
    )
