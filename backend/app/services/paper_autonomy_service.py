"""Safe Alpaca Paper autonomy runner.

This service never enables live trading. It only calls the Chief AI paper bridge
when the user has explicitly enabled demo autonomy and the backend is in
ALPACA_PAPER mode.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from app.agents.ai_team.ai_team_service import AiTeamService
from app.config import Settings
from app.demo_bot_constants import ALPACA_AI_TEAM_WATCHED_SYMBOLS
from app.models.execution_mode import ExecutionMode
from app.services.bot_state_service import BotStateService

logger = logging.getLogger(__name__)


class PaperAutonomyService:
    def __init__(
        self,
        *,
        settings: Settings,
        state: BotStateService,
        ai_team: AiTeamService,
    ) -> None:
        self._settings = settings
        self._state = state
        self._ai_team = ai_team
        self._cycle_lock = threading.Lock()
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None

    def status(self) -> dict[str, Any]:
        return {
            "paper_loop_enabled": bool(self._settings.paper_autonomy_loop_enabled),
            "paper_loop_interval_seconds": int(
                self._settings.paper_autonomy_interval_seconds,
            ),
            "paper_loop_running": self._task is not None and not self._task.done(),
            "paper_confidence_threshold": float(
                self._settings.paper_autonomy_confidence_threshold,
            ),
            "paper_max_open_positions": int(
                self._settings.paper_autonomy_max_open_positions,
            ),
            "paper_max_daily_trades": int(
                self._settings.paper_autonomy_max_daily_trades,
            ),
            "paper_max_position_size": float(
                self._settings.paper_autonomy_max_position_size,
            ),
            "last_cycle_at": self._state.last_paper_cycle_at(),
            "last_cycle_result": self._state.last_paper_cycle_result(),
        }

    def start_background_loop(self) -> None:
        if not self._settings.paper_autonomy_loop_enabled:
            return
        if self._task is not None and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())

    async def stop_background_loop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        interval = max(30, int(self._settings.paper_autonomy_interval_seconds))
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self.run_demo_cycle)
            except Exception as exc:
                logger.warning("Paper autonomy loop cycle failed: %s", exc)
                self._state.set_last_error(str(exc))
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    def run_demo_cycle(self) -> dict[str, Any]:
        if not self._cycle_lock.acquire(blocking=False):
            return self._blocked(cycle_ran=False, reason="Paper autonomy cycle is already running.")
        try:
            blocked = self._preflight_blocked_reason()
            if blocked is not None:
                return self._blocked(cycle_ran=False, reason=blocked)

            initial = self._ai_team.evaluate(
                "AAPL",
                execute_bridge=False,
                append_decision=False,
            )
            selected = self._selected_symbol_from_preview(initial)
            cycle_preview = self._ai_team.evaluate(
                selected,
                execute_bridge=True,
                append_decision=True,
            )
            return self._response_from_preview(cycle_preview)
        except Exception as exc:
            self._state.set_last_error(str(exc))
            return self._blocked(
                cycle_ran=True,
                reason=f"Paper autonomy cycle failed safely: {exc}",
            )
        finally:
            self._cycle_lock.release()

    def _preflight_blocked_reason(self) -> str | None:
        if not self._state.chief_demo_autonomy_enabled():
            return "Chief demo autonomy is disabled."
        if self._state.execution_mode != ExecutionMode.ALPACA_PAPER:
            return "Paper autonomy only runs when execution_mode is ALPACA_PAPER."
        if bool(self._settings.bot_kill_switch):
            return "Kill switch is active."
        if int(self._settings.paper_autonomy_max_open_positions) < 1:
            return "PAPER_AUTONOMY_MAX_OPEN_POSITIONS blocks all new positions."
        return None

    def _selected_symbol_from_preview(self, preview: dict[str, Any]) -> str:
        chief = preview.get("chief_decision")
        selected = str((chief or {}).get("selected_symbol") or "").upper()
        if selected in ALPACA_AI_TEAM_WATCHED_SYMBOLS:
            return selected
        ranked = preview.get("ranked_assets_summary")
        if isinstance(ranked, list) and ranked:
            first = ranked[0]
            if isinstance(first, dict):
                ranked_symbol = str(first.get("symbol") or "").upper()
                if ranked_symbol in ALPACA_AI_TEAM_WATCHED_SYMBOLS:
                    return ranked_symbol
        return "AAPL"

    def _response_from_preview(self, preview: dict[str, Any]) -> dict[str, Any]:
        chief = dict(preview.get("chief_decision") or {})
        bridge = dict(preview.get("execution_bridge") or {})
        agents = list(preview.get("agents") or [])
        risk_agent = _agent_by_name(agents, "Risk & Execution Agent")
        risk_checks = dict(
            risk_agent.get("risk_checks")
            or (risk_agent.get("data_used") or {}).get("risk_checks")
            or {},
        )
        result = {
            "cycle_ran": True,
            "autonomy_enabled": self._state.chief_demo_autonomy_enabled(),
            "execution_mode": self._state.execution_mode.value,
            "live_trading_allowed": False,
            "selected_symbol": str(chief.get("selected_symbol") or preview.get("symbol") or "AAPL"),
            "chief_action": str(chief.get("final_action") or "HOLD"),
            "chief_confidence": float(chief.get("final_confidence") or 0.0),
            "trade_executed": bool(bridge.get("executed")),
            "blocked_reason": bridge.get("skip_reason"),
            "order": bridge.get("order"),
            "decision": chief,
            "risk_checks": risk_checks,
            "agent_summary": chief.get("agent_summary") or {},
        }
        self._state.set_last_paper_cycle_result(_cycle_summary(result))
        return result

    def _blocked(self, *, cycle_ran: bool, reason: str) -> dict[str, Any]:
        result = {
            "cycle_ran": cycle_ran,
            "autonomy_enabled": self._state.chief_demo_autonomy_enabled(),
            "execution_mode": self._state.execution_mode.value,
            "live_trading_allowed": False,
            "selected_symbol": None,
            "chief_action": "HOLD",
            "chief_confidence": 0.0,
            "trade_executed": False,
            "blocked_reason": reason,
            "order": None,
            "decision": {},
            "risk_checks": {},
            "agent_summary": {},
        }
        self._state.set_last_paper_cycle_result(_cycle_summary(result))
        return result


def _agent_by_name(agents: list[Any], name: str) -> dict[str, Any]:
    for item in agents:
        if isinstance(item, dict) and item.get("agent_name") == name:
            return item
    return {}


def _cycle_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "chief_action": result.get("chief_action"),
        "trade_executed": result.get("trade_executed"),
        "blocked_reason": result.get("blocked_reason"),
        "selected_symbol": result.get("selected_symbol"),
        "chief_confidence": result.get("chief_confidence"),
    }
