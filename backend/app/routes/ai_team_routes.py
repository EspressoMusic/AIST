from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.deps import get_ai_team_service
from app.agents.ai_team.ai_team_service import AiTeamService

router = APIRouter(prefix="/ai-team", tags=["ai-team"])


class AiTeamChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    target_agent: Literal["ALL", "RISK", "MACRO", "TECHNICAL", "ASSET_SCOUT", "CHIEF"] = "ALL"
    symbol: str = Field(default="BTCUSDT", min_length=3, max_length=20)


@router.get("/preview")
def preview_ai_team(
    symbol: str = Query(default="BTCUSDT", min_length=3, max_length=20),
    debug: bool = Query(default=False),
    service: AiTeamService = Depends(get_ai_team_service),
) -> dict[str, Any]:
    return service.preview(symbol, debug=debug)


@router.get("/status")
def ai_team_status(
    service: AiTeamService = Depends(get_ai_team_service),
) -> dict[str, Any]:
    return service.status()


@router.post("/chat")
def ai_team_chat(
    request: AiTeamChatRequest,
    service: AiTeamService = Depends(get_ai_team_service),
) -> dict[str, Any]:
    return service.chat(
        message=request.message,
        target_agent=request.target_agent,
        symbol=request.symbol,
    )
