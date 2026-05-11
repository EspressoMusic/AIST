"""Combines agent scores into a directional stance."""

from __future__ import annotations

from datetime import datetime, timezone

from app.demo_bot_constants import DEMO_CONFIDENCE_THRESHOLD, DEMO_MODE
from app.models.agent_model import AgentResultModel

# Legacy blended thresholds when DEMO_MODE rules do not apply.
_STRONG_COMBO_BUY = 12.0
_STRONG_COMBO_SELL = -12.0
_ALIGNED_COMBO_BUY = 6.0
_ALIGNED_COMBO_SELL = -6.0

# In DEMO_MODE OR-directional path: treat tiny scores as unclear -> HOLD.
_WEAK_MAG = 2.0


def decide(
    symbol: str,
    *,
    news_score: float,
    technical_score: float,
    preliminary_side: str,
    risk_approved: bool = False,
    symbol_has_open_trade: bool = False,
) -> AgentResultModel:
    use_demo_directional = (
        DEMO_MODE
        and risk_approved
        and not symbol_has_open_trade
    )

    if use_demo_directional:
        combo = news_score * 0.45 + technical_score * 0.55
        action, align_note = _demo_directional_action(
            news_score,
            technical_score,
            preliminary_side=preliminary_side,
        )
        # Engine rejects opens below DEMO_CONFIDENCE_THRESHOLD; without a floor,
        # mild BUY/SELL tilts often stayed below 40 while strategy still picked a side.
        confidence = max(
            DEMO_CONFIDENCE_THRESHOLD,
            min(abs(news_score) + abs(technical_score) + 26.0, 94.0),
        )
        explanation = (
            f"DEMO_MODE directional: news ({news_score:.1f}), technical ({technical_score:.1f}) "
            f"-> {action}.{align_note}"
        )
        return AgentResultModel(
            agent_name="Strategy Agent",
            symbol=symbol,
            status="completed",
            score=round(combo, 2),
            action=action,
            confidence=round(confidence, 2),
            explanation=explanation,
            created_at=datetime.now(timezone.utc),
        )

    return _legacy_combo_decision(
        symbol,
        news_score=news_score,
        technical_score=technical_score,
        preliminary_side=preliminary_side,
        risk_approved=risk_approved,
    )


def _demo_directional_action(
    news_score: float,
    technical_score: float,
    *,
    preliminary_side: str,
) -> tuple[str, str]:
    """BUY if either score clearly positive; SELL if either clearly negative; else HOLD."""
    if abs(news_score) < _WEAK_MAG and abs(technical_score) < _WEAK_MAG:
        return "HOLD", " Both tilts weak/near zero."

    bull = news_score > 0 or technical_score > 0
    bear = news_score < 0 or technical_score < 0
    if bull and bear:
        if preliminary_side in ("BUY", "SELL"):
            return (
                preliminary_side,
                " Mixed bull/bear — tie-break from technical posture.",
            )
        return "HOLD", " Mixed bull/bear (unclear)."
    if bull:
        return "BUY", " At least one positive tilt."
    if bear:
        return "SELL", " At least one negative tilt."
    return "HOLD", " Flat."


def _legacy_combo_decision(
    symbol: str,
    *,
    news_score: float,
    technical_score: float,
    preliminary_side: str,
    risk_approved: bool,
) -> AgentResultModel:
    combo = news_score * 0.45 + technical_score * 0.55

    aligned_bull = news_score > 0 and technical_score > 0
    aligned_bear = news_score < 0 and technical_score < 0
    use_looser = risk_approved and (aligned_bull or aligned_bear)

    buy_thr = _ALIGNED_COMBO_BUY if use_looser else _STRONG_COMBO_BUY
    sell_thr = _ALIGNED_COMBO_SELL if use_looser else _STRONG_COMBO_SELL

    if combo > buy_thr:
        action = "BUY"
    elif combo < sell_thr:
        action = "SELL"
    else:
        action = "HOLD"

    if action == "HOLD" and preliminary_side in ("BUY", "SELL"):
        action = preliminary_side

    confidence = min(abs(combo) + 28.0, 94.0)

    align_note = ""
    if use_looser and action in ("BUY", "SELL"):
        align_note = " (aligned scores + risk OK -> looser combo threshold)."

    return AgentResultModel(
        agent_name="Strategy Agent",
        symbol=symbol,
        status="completed",
        score=round(combo, 2),
        action=action,
        confidence=round(confidence, 2),
        explanation=(
            f"Blended news ({news_score:.1f}) + technical ({technical_score:.1f}) "
            f"-> stance {action}.{align_note}"
        ),
        created_at=datetime.now(timezone.utc),
    )
