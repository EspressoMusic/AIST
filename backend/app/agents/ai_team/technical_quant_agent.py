"""Technical / Quant Agent."""

from __future__ import annotations

from app.agents.ai_team.base_agent import AgentResponse, AiTeamContext, BaseAiTeamAgent


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    ema = sum(values[:period]) / period
    k = 2.0 / (period + 1.0)
    for value in values[period:]:
        ema = value * k + ema * (1.0 - k)
    return ema


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr_pct(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 2:
        return None
    true_ranges: list[float] = []
    for i in range(1, len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    atr = sum(true_ranges[:period]) / period
    for value in true_ranges[period:]:
        atr = (atr * (period - 1) + value) / period
    last = closes[-1]
    return atr / last * 100.0 if last > 0 else None


class TechnicalQuantAgent(BaseAiTeamAgent):
    agent_name = "Technical / Quant Agent"
    role = "Analyze charts, indicators, volatility, and entry quality."

    def analyze(self, context: AiTeamContext) -> AgentResponse:
        candles = context.technical_candles
        closes = [float(row.get("close") or 0.0) for row in candles if row.get("close") is not None]
        highs = [float(row.get("high") or 0.0) for row in candles if row.get("high") is not None]
        lows = [float(row.get("low") or 0.0) for row in candles if row.get("low") is not None]
        ema_fast = _ema(closes, 12)
        ema_slow = _ema(closes, 26)
        rsi = _rsi(closes, 14)
        volatility = _atr_pct(highs, lows, closes, 14)

        if not closes or ema_fast is None or ema_slow is None or rsi is None or volatility is None:
            return self._mock_response(context)

        recent_trend = (
            (closes[-1] - closes[-10]) / closes[-10] * 100.0
            if len(closes) >= 10 and closes[-10] > 0
            else 0.0
        )
        ema_gap_pct = (ema_fast - ema_slow) / closes[-1] * 100.0 if closes[-1] > 0 else 0.0
        if ema_gap_pct > 0.04 and recent_trend > 0.08:
            trend_direction = "positive"
        elif ema_gap_pct < -0.04 or recent_trend < -0.08:
            trend_direction = "negative"
        else:
            trend_direction = "unclear"

        overbought = rsi >= 70.0
        weak_rsi = rsi <= 35.0
        volatility_penalty = max(0.0, min(20.0, (volatility - 2.5) * 5.0))
        entry_quality_score = max(
            0.0,
            min(
                100.0,
                50.0
                + max(-20.0, min(25.0, ema_gap_pct * 20.0))
                + max(-15.0, min(20.0, recent_trend * 2.0))
                + (10.0 if 42 <= rsi <= 64 else -8.0)
                - volatility_penalty,
            ),
        )

        if trend_direction == "positive" and not overbought and not weak_rsi:
            action = "BUY"
            confidence = min(90.0, 55.0 + entry_quality_score * 0.38)
            risk_level = "MEDIUM" if volatility >= 2.5 else "LOW"
            short_reason = "Trend positive and RSI is acceptable"
        elif trend_direction == "negative" or overbought or weak_rsi:
            action = "SELL"
            confidence = min(88.0, 52.0 + max(20.0, 100.0 - entry_quality_score) * 0.32)
            risk_level = "HIGH" if overbought or volatility >= 3.5 else "MEDIUM"
            short_reason = "Trend or RSI is risky"
        else:
            action = "HOLD"
            confidence = 58.0
            risk_level = "MEDIUM"
            short_reason = "Trend is unclear"

        indicators = {
            "ema_fast": round(ema_fast, 8),
            "ema_slow": round(ema_slow, 8),
            "rsi": round(rsi, 3),
            "volatility": round(volatility, 4),
            "trend_direction": trend_direction,
            "entry_quality_score": round(entry_quality_score, 2),
        }
        source_label = (
            "Alpaca stock bars"
            if context.execution_mode == "ALPACA_PAPER"
            else "Binance public klines"
        )
        reason = (
            f"{source_label}: trend={trend_direction}, RSI={rsi:.1f}, "
            f"EMA gap={ema_gap_pct:.3f}%, ATR volatility={volatility:.3f}%, "
            f"entry quality={entry_quality_score:.1f}."
        )

        return self.response(
            action=action,  # type: ignore[arg-type]
            confidence=confidence,
            risk_level=risk_level,  # type: ignore[arg-type]
            veto=False,
            short_reason=short_reason,
            reason=reason,
            data_used={
                "indicators": indicators,
                **indicators,
                "current_status": context.technical_current_status,
                "data_sources": context.technical_data_sources,
                "fallback_reason": context.technical_fallback_reason,
                "candle_count": len(candles),
                "interval": "15m",
                "macd": "placeholder",
                "support_resistance": "placeholder",
                "entry_exit_quality": short_reason,
                "ema_gap_pct": round(ema_gap_pct, 4),
                "recent_trend_pct": round(recent_trend, 4),
            },
        )

    def _mock_response(self, context: AiTeamContext) -> AgentResponse:
        prices = list(context.prices.values())
        peer_avg = sum(prices) / len(prices) if prices else context.current_price
        relative_strength = (
            (context.current_price - peer_avg) / peer_avg * 100.0 if peer_avg > 0 else 0.0
        )
        ema_fast = context.current_price * (1.0 + relative_strength / 12000.0)
        ema_slow = context.current_price * (1.0 - relative_strength / 16000.0)
        rsi = max(25.0, min(75.0, 50.0 + relative_strength * 1.8))
        volatility = max(0.25, min(4.0, abs(relative_strength) * 0.18 + 0.75))
        trend_direction = "positive" if ema_fast > ema_slow else "negative"
        entry_quality_score = max(0.0, min(100.0, 52.0 + relative_strength))
        return self.response(
            action="HOLD",
            confidence=52.0,
            risk_level="MEDIUM",
            veto=False,
            short_reason="Technical data fallback is active",
            reason="Public kline data was unavailable, so the agent used safe mock indicators.",
            data_used={
                "indicators": {
                    "ema_fast": round(ema_fast, 8),
                    "ema_slow": round(ema_slow, 8),
                    "rsi": round(rsi, 3),
                    "volatility": round(volatility, 4),
                    "trend_direction": trend_direction,
                    "entry_quality_score": round(entry_quality_score, 2),
                },
                "ema_fast": round(ema_fast, 8),
                "ema_slow": round(ema_slow, 8),
                "rsi": round(rsi, 3),
                "volatility": round(volatility, 4),
                "trend_direction": trend_direction,
                "entry_quality_score": round(entry_quality_score, 2),
                "current_status": "MOCK",
                "data_sources": ["mock_technical_indicators"],
                "fallback_reason": context.technical_fallback_reason,
            },
        )
