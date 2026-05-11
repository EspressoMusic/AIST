"""Risk gate — exposure, streaks, volatility stress (mock rules, veto capable)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.demo_bot_constants import (
    DEMO_CONFIDENCE_THRESHOLD,
    DEMO_MODE,
    DEMO_RISK_SCORE_THRESHOLD,
    MAX_OPEN_POSITIONS,
)
from app.models.agent_model import AgentResultModel


def evaluate(
    symbol: str,
    *,
    news_score: float,
    technical_score: float,
    open_positions: int,
    market_volatility: float | None = None,
    consecutive_losses_symbol: int = 0,
    exec_gate_pnl_today: float = 0.0,
    drawdown_proxy: float = 0.0,
    ai_client: Any | None = None,
) -> AgentResultModel:
    stress = abs(news_score) + abs(technical_score)
    vol_bump = 0.0
    if market_volatility is not None:
        vol_bump = min(22.0, market_volatility * 9000.0)

    streak_penalty = min(28.0, consecutive_losses_symbol * 7.0)
    dd_penalty = min(18.0, abs(drawdown_proxy) / 250.0)
    daily_penalty = 0.0
    if exec_gate_pnl_today < 0:
        daily_penalty = min(25.0, abs(exec_gate_pnl_today) / 40.0)

    # Higher risk_score => safer in this demo scale.
    risk_score = max(
        5.0,
        min(
            95.0,
            74.0
            - open_positions * 6.0
            - stress * 0.14
            - vol_bump
            - streak_penalty
            - dd_penalty
            - daily_penalty,
        ),
    )

    hard_veto = consecutive_losses_symbol >= 4
    approved = (
        open_positions < MAX_OPEN_POSITIONS
        and risk_score >= DEMO_RISK_SCORE_THRESHOLD
        and not hard_veto
    )

    reasons = [
        f"open_positions={open_positions}/{MAX_OPEN_POSITIONS}",
        f"composite_stress={stress:.1f}",
        f"market_volatility_hint={market_volatility}",
        f"symbol_loss_streak_closed={consecutive_losses_symbol}",
        f"exec_gate_realized_pnl_today={exec_gate_pnl_today:.2f}",
        f"drawdown_proxy={drawdown_proxy:.2f}",
    ]
    if hard_veto:
        reasons.append("Hard veto: extended loss streak on this symbol (mock rule).")
    payload: dict[str, Any] = {
        "approved": approved,
        "risk_score": round(risk_score, 2),
        "vetoes": ([] if approved else ["risk_threshold_or_hard_veto"]),
        "reasons": reasons,
        "symbol": symbol.strip().upper(),
    }
    if ai_client is not None:
        payload["ai_advice"] = ai_client.analyze_with_ai(
            (
                "Risk explanation only. Do not execute trades. "
                f"Symbol={symbol}. Approved={approved}. Risk score={risk_score:.2f}. "
                f"Open positions={open_positions}. Market volatility={market_volatility}. "
                f"Loss streak={consecutive_losses_symbol}. Today P/L={exec_gate_pnl_today:.2f}. "
                f"Drawdown proxy={drawdown_proxy:.2f}. Reasons={reasons}"
            ),
            None,
        )
        payload["ai_provider"] = ai_client.status()

    return AgentResultModel(
        agent_name="Risk Agent",
        symbol=symbol,
        status="approved" if approved else "rejected",
        score=round(risk_score, 2),
        action=None,
        confidence=round(min(risk_score + 8.0, 99.0), 2),
        explanation=(
            f"DEMO_MODE={DEMO_MODE}; gate={'PASS' if approved else 'BLOCK'}; "
            f"threshold risk_score>={DEMO_RISK_SCORE_THRESHOLD} "
            f"(engine may also require confidence>={DEMO_CONFIDENCE_THRESHOLD} on paper). "
            + " ".join(reasons)
        ),
        created_at=datetime.now(timezone.utc),
        payload=payload,
    )
