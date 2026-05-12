from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.demo_bot_constants import CHIEF_ALLOWED_DEMO_MODES
from app.deps import get_bot_state_service, get_paper_autonomy_service
from app.services.bot_state_service import BotStateService
from app.services.paper_autonomy_service import PaperAutonomyService

router = APIRouter(prefix="/chief-bot", tags=["chief-bot"])


def _status(
    state: BotStateService,
    paper_autonomy: PaperAutonomyService | None = None,
) -> dict[str, Any]:
    paper_status = paper_autonomy.status() if paper_autonomy is not None else {}
    return {
        "enabled": state.chief_demo_autonomy_enabled(),
        "execution_mode": state.execution_mode.value,
        "allowed_modes": list(CHIEF_ALLOWED_DEMO_MODES),
        "live_trading_allowed": False,
        "last_chief_decision": state.last_chief_decision(),
        "paper_loop_enabled": paper_status.get("paper_loop_enabled", False),
        "paper_loop_interval_seconds": paper_status.get("paper_loop_interval_seconds", 300),
        "paper_loop_running": paper_status.get("paper_loop_running", False),
        "paper_confidence_threshold": paper_status.get("paper_confidence_threshold", 75.0),
        "paper_max_open_positions": paper_status.get("paper_max_open_positions", 1),
        "paper_max_daily_trades": paper_status.get("paper_max_daily_trades", 3),
        "paper_max_position_size": paper_status.get("paper_max_position_size", 1000.0),
        "last_cycle_at": paper_status.get("last_cycle_at"),
        "last_cycle_result": paper_status.get("last_cycle_result"),
    }


@router.get("/status")
def chief_bot_status(
    state: BotStateService = Depends(get_bot_state_service),
    paper_autonomy: PaperAutonomyService = Depends(get_paper_autonomy_service),
) -> dict[str, Any]:
    return _status(state, paper_autonomy)


@router.post("/enable-demo-autonomy")
def enable_demo_autonomy(
    state: BotStateService = Depends(get_bot_state_service),
    paper_autonomy: PaperAutonomyService = Depends(get_paper_autonomy_service),
) -> dict[str, Any]:
    state.set_chief_demo_autonomy_enabled(True)
    return _status(state, paper_autonomy)


@router.post("/disable-demo-autonomy")
def disable_demo_autonomy(
    state: BotStateService = Depends(get_bot_state_service),
    paper_autonomy: PaperAutonomyService = Depends(get_paper_autonomy_service),
) -> dict[str, Any]:
    state.set_chief_demo_autonomy_enabled(False)
    return _status(state, paper_autonomy)


@router.post("/run-demo-cycle")
def run_demo_cycle(
    paper_autonomy: PaperAutonomyService = Depends(get_paper_autonomy_service),
) -> dict[str, Any]:
    return paper_autonomy.run_demo_cycle()
