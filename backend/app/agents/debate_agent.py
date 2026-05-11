"""Strategy debate — merges agent views (mock); LLM can wrap later."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.demo_bot_constants import (
    DEMO_TRADE_NOTIONAL_USD,
    TESTNET_DEV_SL_PCT,
    TESTNET_DEV_TP_PCT,
    TESTNET_MARKET_BUY_QUOTE_USDT,
)
from app.models.agent_model import AgentResultModel
from app.models.execution_mode import ExecutionMode


def _vote_from_sentiment(sentiment: str) -> str:
    s = sentiment.lower()
    if s == "bullish":
        return "BUY"
    if s == "bearish":
        return "SELL"
    return "HOLD"


def deliberate(
    symbol: str,
    *,
    market: AgentResultModel,
    technical: AgentResultModel,
    news: AgentResultModel,
    risk: AgentResultModel,
    learning: AgentResultModel,
    execution_mode: ExecutionMode,
    ai_client: Any | None = None,
) -> AgentResultModel:
    """Tally mock votes, apply learning guardrails, emit sizing + TP/SL hints."""
    tech_vote = (technical.action or "HOLD").upper()
    npayload = news.payload or {}
    news_vote = _vote_from_sentiment(str(npayload.get("sentiment", "neutral")))
    lp = learning.payload or {}
    block_buy = bool(lp.get("block_new_buys_on_symbol"))
    mult = float(lp.get("confidence_multiplier") or 1.0)

    votes: list[dict[str, Any]] = [
        {"agent": "Technical Analysis Agent", "vote": tech_vote, "weight": 1.15},
        {"agent": "News & Sentiment Agent", "vote": news_vote, "weight": 0.95},
        {"agent": "Market Data Agent", "vote": _slope_vote(market), "weight": 0.75},
    ]

    tally = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
    for v in votes:
        w = float(v["weight"])
        tally[str(v["vote"]).upper()] = tally.get(str(v["vote"]).upper(), 0.0) + w

    reasons: list[str] = [
        f"Weighted tally: BUY={tally['BUY']:.2f} SELL={tally['SELL']:.2f} HOLD={tally['HOLD']:.2f}.",
    ]

    if block_buy:
        tally["BUY"] = 0.0
        reasons.append("Learning: consecutive losses — block fresh BUY on this symbol.")

    winner = max(tally, key=tally.get)
    if tally[winner] == 0.0 or winner == "HOLD":
        final_action = "HOLD"
    else:
        final_action = winner

    if risk.status != "approved":
        final_action = "HOLD"
        reasons.append("Risk veto — debate output forced to HOLD.")

    base_conf = min(
        float(technical.confidence or 55.0),
        float(news.confidence or 55.0),
        float(market.confidence or 55.0),
    )
    spread_pen = abs(tally["BUY"] - tally["SELL"])
    conf = max(38.0, min(94.0, base_conf * mult + spread_pen * 2.0))
    if final_action == "HOLD":
        conf = min(conf, 72.0)

    risk_level = "MEDIUM"
    if conf >= 82:
        risk_level = "LOW"
    elif conf <= 48:
        risk_level = "HIGH"

    if execution_mode == ExecutionMode.BINANCE_TESTNET:
        pos_usdt = float(TESTNET_MARKET_BUY_QUOTE_USDT)
        tp_pct = float(TESTNET_DEV_TP_PCT)
        sl_pct = float(TESTNET_DEV_SL_PCT)
    else:
        pos_usdt = float(DEMO_TRADE_NOTIONAL_USD)
        tp_pct = 1.0
        sl_pct = -0.5

    ai_advice: dict[str, Any] | None = None
    if ai_client is not None:
        ai_advice = ai_client.analyze_with_ai(
            (
                "Debate coordinator summary only. Do not execute trades. "
                "Summarize agent opinions into a final recommendation that still "
                "requires execution-gate approval. "
                f"Symbol={symbol}. Vote tally={tally}. Current final_action={final_action}. "
                f"Risk approved={risk.status == 'approved'}. Learning block buy={block_buy}. "
                f"Technical payload={technical.payload}. News payload={news.payload}. "
                f"Risk payload={risk.payload}. Learning payload={learning.payload}."
            ),
            None,
        )
        ai_action = str(ai_advice.get("action") or "HOLD").upper()
        ai_conf = float(ai_advice.get("confidence") or 0.0)
        if bool(ai_advice.get("veto")):
            final_action = "HOLD"
            reasons.append("AI advisor vetoed the setup; debate recommendation forced to HOLD.")
        elif risk.status == "approved" and not block_buy and ai_conf >= 70 and ai_action in {"BUY", "SELL", "HOLD"}:
            final_action = ai_action
            conf = min(94.0, max(conf, ai_conf))
            reasons.append(f"AI advisor reinforced final recommendation: {ai_action}.")
        risk_level = str(ai_advice.get("risk_level") or risk_level).upper()

    agent_votes = [*votes, {"agent": "Risk Agent", "vote": "APPROVE" if risk.status == "approved" else "VETO", "weight": 1.4}]
    agent_votes.append(
        {
            "agent": "Performance Learning Agent",
            "vote": "BLOCK_BUY" if block_buy else "OK",
            "weight": 1.2,
        },
    )
    if ai_advice is not None:
        agent_votes.append(
            {
                "agent": "AI Advisor",
                "vote": ai_advice["action"],
                "weight": 0.8,
                "confidence": ai_advice["confidence"],
                "veto": ai_advice["veto"],
            },
        )

    final_reasons = [
        *reasons,
        f"Chosen action={final_action} after risk + learning gates.",
        f"risk_level={risk_level} position_size_usdt={pos_usdt:.2f} tp_pct={tp_pct} sl_pct={sl_pct}",
    ]

    payload: dict[str, Any] = {
        "provider": "mock_majority_vote",
        "final_action": final_action,
        "final_confidence": round(conf, 2),
        "final_reasons": final_reasons,
        "risk_level": risk_level,
        "position_size_usdt": round(pos_usdt, 2),
        "take_profit_pct": tp_pct,
        "stop_loss_pct": sl_pct,
        "agent_votes": agent_votes,
        "disagreement_notes": _disagreement_notes(tech_vote, news_vote),
    }
    if ai_advice is not None:
        payload["ai_advice"] = ai_advice
        payload["ai_provider"] = ai_client.status()

    return AgentResultModel(
        agent_name="Strategy Debate Agent",
        symbol=symbol,
        status="completed",
        score=round(tally.get(final_action, 0.0), 2),
        action=final_action,
        confidence=round(conf, 2),
        explanation=" ".join(final_reasons),
        created_at=datetime.now(timezone.utc),
        payload=payload,
    )


def _slope_vote(market: AgentResultModel) -> str:
    mp = market.payload or {}
    slope = float(mp.get("trend_slope_10") or 0.0)
    if slope > 0.0004:
        return "BUY"
    if slope < -0.0004:
        return "SELL"
    return "HOLD"


def _disagreement_notes(tech: str, news: str) -> list[str]:
    notes: list[str] = []
    if tech != news and tech != "HOLD" and news != "HOLD":
        notes.append(f"Technical ({tech}) disagrees with news tilt ({news}).")
    elif tech != news:
        notes.append(f"Mixed alignment: technical={tech}, news={news}.")
    return notes
