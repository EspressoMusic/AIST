"""Non-AI execution gate — hard safety limits (recommendations never bypass this)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.models.decision_model import DecisionModel
from app.demo_bot_constants import (
    EXEC_GATE_DAILY_MAX_LOSS_USDT,
    EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS,
    EXEC_GATE_MAX_OPENS_PER_DAY,
)
from app.models.agent_model import AgentResultModel
from app.services.bot_state_service import BotStateService


def evaluate_gate(
    *,
    settings: Settings,
    state: BotStateService,
    decision: DecisionModel,
    proposed_action: str,
) -> tuple[str | None, dict[str, Any], AgentResultModel]:
    """
    Returns (skip_reason or None, diagnostics dict, agent-shaped log row).
    Only blocks **new opens** (BUY in paper/testnet); SELL / HOLD pass through here.
    """
    checks: list[dict[str, Any]] = []
    sym = decision.symbol.strip().upper()

    def _ok(name: str, passed: bool, detail: str) -> None:
        checks.append({"rule": name, "passed": passed, "detail": detail})

    if settings.bot_kill_switch:
        _ok("kill_switch", False, "BOT_KILL_SWITCH / settings.bot_kill_switch enabled.")
        return _fail(sym, checks, "Kill switch enabled.")

    if proposed_action.upper() != "BUY":
        _ok("open_intent", True, "No BUY open intent — gate not blocking.")
        return _pass(sym, checks)

    snap = state.exec_gate_snapshot()
    _ok("daily_max_trades", True, f"opens_today={snap['opens_today']} cap={EXEC_GATE_MAX_OPENS_PER_DAY}")
    if int(snap["opens_today"]) >= EXEC_GATE_MAX_OPENS_PER_DAY:
        checks[-1]["passed"] = False
        return _fail(sym, checks, "Daily max opens reached.")

    pnl_today = float(snap["realized_pnl_today"])
    _ok(
        "daily_max_loss",
        pnl_today > EXEC_GATE_DAILY_MAX_LOSS_USDT,
        f"realized_pnl_today={pnl_today:.2f} floor={EXEC_GATE_DAILY_MAX_LOSS_USDT}",
    )
    if pnl_today <= EXEC_GATE_DAILY_MAX_LOSS_USDT:
        checks[-1]["passed"] = False
        return _fail(sym, checks, "Daily max loss (realized) breached.")

    if EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS > 0:
        last_raw = snap.get("last_open_utc")
        if isinstance(last_raw, str):
            last_open = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
        else:
            last_open = None
        if last_open is not None:
            delta = (state.utc_now() - last_open).total_seconds()
            ok_cd = delta >= EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS
            _ok(
                "global_open_cooldown",
                ok_cd,
                f"seconds_since_last_open={delta:.0f} required={EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS}",
            )
            if not ok_cd:
                return _fail(sym, checks, "Global open cooldown active.")
        else:
            _ok("global_open_cooldown", True, "No prior open today.")
    else:
        _ok("global_open_cooldown", True, "Disabled (EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS=0).")

    _ok("max_one_open_position", True, "Enforced separately in engine for BUY path.")
    _ok("max_order_size", True, "Order notional capped in engine constants.")

    return _pass(sym, checks)


def _pass(symbol: str, checks: list[dict[str, Any]]) -> tuple[None, dict[str, Any], AgentResultModel]:
    diag: dict[str, Any] = {"symbol": symbol, "allowed": True, "checks": checks}
    agent = _agent_row(symbol, "PASS", diag)
    return None, diag, agent


def _fail(
    symbol: str,
    checks: list[dict[str, Any]],
    reason: str,
) -> tuple[str, dict[str, Any], AgentResultModel]:
    diag: dict[str, Any] = {"symbol": symbol, "allowed": False, "checks": checks, "reason": reason}
    agent = _agent_row(symbol, "BLOCK", diag, reason)
    return reason, diag, agent


def _agent_row(symbol: str, verdict: str, diag: dict[str, Any], reason: str = "") -> AgentResultModel:
    return AgentResultModel(
        agent_name="Execution Gate",
        symbol=symbol,
        status="completed",
        score=100.0 if verdict == "PASS" else 0.0,
        action=verdict,
        confidence=99.0,
        explanation=reason or "All execution gate checks passed.",
        created_at=datetime.now(timezone.utc),
        payload=diag,
    )
