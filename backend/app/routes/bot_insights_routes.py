from fastapi import APIRouter, Depends

from app.deps import get_bot_state_service
from app.models.bot_api_model import (
    AgentsLatestResponse,
    DecisionsListResponse,
    LessonsListResponse,
)
from app.services.bot_state_service import BotStateService

router = APIRouter(tags=["bot-brain"])


@router.get("/decisions", response_model=DecisionsListResponse)
def list_decisions(
    state: BotStateService = Depends(get_bot_state_service),
) -> DecisionsListResponse:
    return DecisionsListResponse(decisions=state.decisions_newest_first())


@router.get("/agents/latest", response_model=AgentsLatestResponse)
def latest_agents(
    state: BotStateService = Depends(get_bot_state_service),
) -> AgentsLatestResponse:
    return AgentsLatestResponse(agents=state.latest_agents())


@router.get("/lessons", response_model=LessonsListResponse)
def list_lessons(
    state: BotStateService = Depends(get_bot_state_service),
) -> LessonsListResponse:
    return LessonsListResponse(lessons=state.lessons_newest_first())
