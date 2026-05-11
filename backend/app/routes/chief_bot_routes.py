from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.demo_bot_constants import CHIEF_ALLOWED_DEMO_MODES
from app.deps import get_bot_state_service
from app.services.bot_state_service import BotStateService

router = APIRouter(prefix="/chief-bot", tags=["chief-bot"])


def _status(state: BotStateService) -> dict[str, Any]:
    return {
        "enabled": state.chief_demo_autonomy_enabled(),
        "execution_mode": state.execution_mode.value,
        "allowed_modes": list(CHIEF_ALLOWED_DEMO_MODES),
        "live_trading_allowed": False,
        "last_chief_decision": state.last_chief_decision(),
    }


@router.get("/status")
def chief_bot_status(
    state: BotStateService = Depends(get_bot_state_service),
) -> dict[str, Any]:
    return _status(state)


@router.post("/enable-demo-autonomy")
def enable_demo_autonomy(
    state: BotStateService = Depends(get_bot_state_service),
) -> dict[str, Any]:
    state.set_chief_demo_autonomy_enabled(True)
    return _status(state)


@router.post("/disable-demo-autonomy")
def disable_demo_autonomy(
    state: BotStateService = Depends(get_bot_state_service),
) -> dict[str, Any]:
    state.set_chief_demo_autonomy_enabled(False)
    return _status(state)
