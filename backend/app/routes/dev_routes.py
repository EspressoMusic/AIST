from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.deps import get_bot_state_service
from app.services.bot_state_service import BotStateService

router = APIRouter(prefix="/dev", tags=["development"])


@router.post("/reset-demo-state")
def reset_demo_state(
    state: BotStateService = Depends(get_bot_state_service),
) -> dict[str, Any]:
    """Development-only reset. Clears volatile demo state; never touches .env or keys."""
    state.reset_demo_state()
    return {
        "development_only": True,
        "message": "Demo state reset. API keys and .env were not touched.",
        "portfolio": {
            "starting_balance": 10000.0,
            "current_value": 10000.0,
            "total_profit_loss": 0.0,
            "realized_profit_loss": 0.0,
            "unrealized_profit_loss": 0.0,
            "open_trades_count": 0,
            "closed_trades_count": 0,
        },
    }
