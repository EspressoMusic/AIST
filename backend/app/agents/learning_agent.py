"""Performance-aware learning — mock adjustments (LLM-ready context)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from app.models.agent_model import AgentResultModel
from app.models.demo_trade import DemoTrade
from app.models.lesson_model import LessonModel
from app.models.performance_model import PerformanceResponse


def analyze_pipeline(
    symbol: str,
    *,
    lessons_recent_count: int,
    seed_mod: float,
    performance: PerformanceResponse | None,
    consecutive_losses_symbol: int,
    drawdown_proxy: float,
    ai_client: Any | None = None,
) -> AgentResultModel:
    sym = symbol.strip().upper()
    perf_total = 0
    sym_row = None
    if performance is not None:
        perf_total = performance.total_trades
        for row in performance.symbols:
            if row.symbol == sym:
                sym_row = row
                break

    block_symbol = consecutive_losses_symbol >= 3
    conf_mult = 1.0
    if consecutive_losses_symbol >= 2:
        conf_mult *= 0.88
    if sym_row is not None and sym_row.losing_trades >= 3 and sym_row.total_realized_profit_loss < 0:
        conf_mult *= 0.82
    if drawdown_proxy < -150.0:
        conf_mult *= 0.9

    tone = (
        "Baseline posture until more closed trades exist."
        if perf_total == 0
        else f"Scoped memory: {perf_total} closed trade(s); streak_losses={consecutive_losses_symbol}."
    )
    score = min(92.0, 44.0 + lessons_recent_count * 3.5 + (seed_mod % 7))
    reasons = [
        tone,
        f"confidence_multiplier={conf_mult:.3f}",
        f"block_new_buys_on_symbol={block_symbol}",
    ]

    payload: dict[str, Any] = {
        "provider": "mock_performance_rules",
        "symbol": sym,
        "lessons_recent_count": lessons_recent_count,
        "performance_total_trades": perf_total,
        "symbol_summary": None if sym_row is None else sym_row.model_dump(mode="json"),
        "consecutive_losses_closed": consecutive_losses_symbol,
        "drawdown_proxy": drawdown_proxy,
        "confidence_multiplier": round(conf_mult, 4),
        "block_new_buys_on_symbol": block_symbol,
        "reasons": reasons,
        "future_llm": "Pass recent_trades_json + performance JSON into structured prompt.",
    }
    if ai_client is not None:
        payload["ai_advice"] = ai_client.analyze_with_ai(
            (
                "Performance learning interpretation only. Do not execute trades. "
                f"Symbol={sym}. Total closed trades={perf_total}. "
                f"Consecutive losses={consecutive_losses_symbol}. "
                f"Drawdown proxy={drawdown_proxy:.2f}. "
                f"Confidence multiplier={conf_mult:.3f}. "
                f"Block new buys={block_symbol}. Symbol summary={payload['symbol_summary']}. "
                f"Reasons={reasons}"
            ),
            None,
        )
        payload["ai_provider"] = ai_client.status()

    return AgentResultModel(
        agent_name="Performance Learning Agent",
        symbol=symbol,
        status="completed",
        score=round(score, 2),
        action="LEARN",
        confidence=round(52.0 + min(30.0, perf_total * 1.5), 2),
        explanation=" ".join(reasons),
        created_at=datetime.now(timezone.utc),
        payload=payload,
    )


def lesson_from_closed_trade(trade: DemoTrade) -> LessonModel:
    ok = float(trade.profit_loss or 0.0) >= 0
    rng = random.Random(abs(hash(str(trade.id))) % (2**32))
    templates_ok = [
        (
            "Exit timing aligned with the simulated swing.",
            "Repeat similar setups when risk gate stays permissive.",
        ),
        (
            "Momentum fade matched demo take-profit heuristic.",
            "Consider trimming earlier when volatility spikes.",
        ),
    ]
    templates_bad = [
        (
            "Loss exceeded comfortable demo stop envelope.",
            "Tighten hypothetical stops when sentiment diverges from tape.",
        ),
        (
            "Late exit amplified adverse excursion.",
            "Define earlier flatten triggers for marginal setups.",
        ),
    ]
    lesson_t, improve_t = rng.choice(templates_ok if ok else templates_bad)
    return LessonModel(
        trade_id=trade.id,
        symbol=trade.symbol,
        was_successful=ok,
        lesson=lesson_t,
        improvement_suggestion=improve_t,
        created_at=datetime.now(timezone.utc),
    )
