from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.deps import get_bot_state_service
from app.services.bot_state_service import BotStateService

router = APIRouter(prefix="/demo-week", tags=["demo-week"])


@router.get("/status")
def demo_week_status(
    state: BotStateService = Depends(get_bot_state_service),
) -> dict[str, Any]:
    return state.demo_week_status()


@router.post("/enable")
def enable_demo_week(
    state: BotStateService = Depends(get_bot_state_service),
) -> dict[str, Any]:
    state.set_demo_week_enabled(True)
    return state.demo_week_status()


@router.post("/disable")
def disable_demo_week(
    state: BotStateService = Depends(get_bot_state_service),
) -> dict[str, Any]:
    state.set_demo_week_enabled(False)
    return state.demo_week_status()
