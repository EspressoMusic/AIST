"""Maps multi-agent brain outputs into DecisionModel (execution stays in bot engine)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.agent_model import AgentResultModel
from app.models.decision_model import DecisionModel


def compose_from_brain(
    symbol: str,
    *,
    market: AgentResultModel,
    technical: AgentResultModel,
    news: AgentResultModel,
    risk: AgentResultModel,
    learning: AgentResultModel,
    debate: AgentResultModel,
) -> DecisionModel:
    """Merge debate + hard coordinator rules (learning symbol block, risk veto)."""
    dp = debate.payload or {}
    risk_ok = risk.status == "approved"
    base_action = str(dp.get("final_action") or debate.action or "HOLD").upper()
    block_buy = bool((learning.payload or {}).get("block_new_buys_on_symbol"))

    final_action = base_action
    if not risk_ok:
        final_action = "HOLD"
    elif block_buy and final_action == "BUY":
        final_action = "HOLD"

    confidence = float(dp.get("final_confidence") or debate.confidence or 0.0)
    if not risk_ok:
        confidence = min(confidence, float(risk.confidence or 40.0))
    if block_buy:
        confidence = min(confidence, 55.0)

    final_reasons: list[str] = list(dp.get("final_reasons") or [debate.explanation])
    if block_buy and base_action == "BUY" and final_action == "HOLD" and risk_ok:
        final_reasons.append("Coordinator: learning block on symbol (3+ consecutive losses).")
    explanation = " ".join(final_reasons)

    brain: dict[str, Any] = {
        "market_data_agent": market.model_dump(mode="json"),
        "technical_agent": technical.model_dump(mode="json"),
        "news_agent": news.model_dump(mode="json"),
        "risk_agent": risk.model_dump(mode="json"),
        "learning_agent": learning.model_dump(mode="json"),
        "debate_agent": debate.model_dump(mode="json"),
        "final_action": final_action,
        "final_confidence": round(confidence, 2),
        "final_reasons": final_reasons,
        "execution_gate": None,
    }

    return DecisionModel(
        symbol=symbol,
        final_action=final_action,
        confidence=round(confidence, 2),
        final_confidence=round(confidence, 2),
        final_reasons=final_reasons,
        news_score=news.score,
        technical_score=technical.score,
        risk_score=risk.score,
        risk_approved=risk_ok,
        explanation=explanation,
        brain=brain,
        created_at=datetime.now(timezone.utc),
    )


def compose(
    symbol: str,
    *,
    strategy: AgentResultModel,
    risk: AgentResultModel,
    news: AgentResultModel,
    technical: AgentResultModel,
) -> DecisionModel:
    """Legacy compose path (kept for tests / tooling)."""
    from app.demo_bot_constants import DEMO_MODE

    risk_ok = risk.status == "approved"
    side = strategy.action or "HOLD"
    if not risk_ok:
        side = "HOLD"

    if DEMO_MODE:
        confidence = min(float(strategy.confidence or 0), float(risk.confidence or 0))
    else:
        confidence = min(
            float(strategy.confidence or 0),
            float(risk.confidence or 0),
            (float(technical.confidence or 0) + float(news.confidence or 0)) / 2,
        )

    why_parts = [
        f"Strategy proposes {strategy.action} with blended score {strategy.score}.",
        f"Risk gate {'approved' if risk_ok else 'blocked'} ({risk.explanation}).",
        f"News tilt {news.score}, technical tilt {technical.score}.",
    ]
    return DecisionModel(
        symbol=symbol,
        final_action=side,
        confidence=round(confidence, 2),
        news_score=news.score,
        technical_score=technical.score,
        risk_score=risk.score,
        risk_approved=risk_ok,
        explanation=" ".join(why_parts),
        created_at=datetime.now(timezone.utc),
    )
