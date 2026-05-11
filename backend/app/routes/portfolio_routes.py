from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.deps import get_portfolio_service
from app.models.portfolio_model import PortfolioResponse
from app.services.portfolio_service import PortfolioService

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio(
    portfolio: PortfolioService = Depends(get_portfolio_service),
) -> JSONResponse:
    """Return full portfolio JSON (all fields) via JSONResponse for reliable serialization."""
    payload = portfolio.get_portfolio()
    return JSONResponse(content=jsonable_encoder(payload))
