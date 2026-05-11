from fastapi import APIRouter, Depends

from app.deps import get_exchange_service
from app.models.market_model import MarketPricesResponse
from app.services.exchange_service import ExchangeService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices", response_model=MarketPricesResponse)
def get_prices(
    exchange: ExchangeService = Depends(get_exchange_service),
) -> MarketPricesResponse:
    return exchange.get_prices()
