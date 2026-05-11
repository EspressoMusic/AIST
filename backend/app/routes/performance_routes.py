from fastapi import APIRouter, Depends

from app.deps import get_bot_state_service
from app.models.performance_model import PerformanceResponse
from app.services.bot_state_service import BotStateService
from app.services.performance_service import build_performance_response

router = APIRouter(tags=["performance"])


@router.get(
    "/performance",
    response_model=PerformanceResponse,
    summary="Closed-trade performance (same scope as GET /trades history)",
)
def get_performance(
    state: BotStateService = Depends(get_bot_state_service),
) -> PerformanceResponse:
    """Aggregate metrics over **closed** trades for the current ``execution_mode`` source filter."""
    return build_performance_response(state)
