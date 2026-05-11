"""Execution helper — paper simulation or Spot Testnet (never mainnet)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.agent_model import AgentResultModel
from app.models.execution_mode import ExecutionMode


def summarize_execution(
    symbol: str,
    *,
    opened: bool,
    closed_ids: list[str],
    skip_reason: str | None = None,
    execution_mode: ExecutionMode = ExecutionMode.PAPER_DEMO,
    extra_detail: str = "",
) -> AgentResultModel:
    testnet_close = any(c.startswith("tn-close-") for c in closed_ids)
    demo_closes = [c for c in closed_ids if not c.startswith("tn-close-")]

    if skip_reason:
        detail = f"No new execution: {skip_reason}"
        action_txt = "NO_OPEN"
        score = 0.0
    elif opened:
        layer = (
            "Spot Testnet"
            if execution_mode == ExecutionMode.BINANCE_TESTNET
            else "simulated"
        )
        detail = f"Opened {layer} position on {symbol}."
        action_txt = (
            "OPEN_TESTNET"
            if execution_mode == ExecutionMode.BINANCE_TESTNET
            else "OPEN_SIM"
        )
        score = 100.0
    elif testnet_close:
        detail = (
            f"Spot Testnet MARKET SELL on {symbol}. "
            f"Closed refs: {', '.join(closed_ids)}."
        )
        action_txt = "CLOSE_TESTNET"
        score = 100.0
    else:
        detail = "No new position opened (no BUY/SELL signal)."
        action_txt = "NO_OPEN"
        score = 55.0

    if demo_closes:
        detail += f" Closed demo ids: {', '.join(demo_closes)}."

    if execution_mode == ExecutionMode.PAPER_DEMO:
        tail = " Paper demo only — no exchange orders."
    else:
        tail = " Binance Spot Testnet only — not mainnet; test funds."

    if extra_detail:
        tail = f" {extra_detail.strip()}{tail}"

    return AgentResultModel(
        agent_name="Execution Agent",
        symbol=symbol,
        status="completed",
        score=score,
        action=action_txt,
        confidence=99.5 if score >= 100.0 else 55.0,
        explanation=detail + tail,
        created_at=datetime.now(timezone.utc),
    )
