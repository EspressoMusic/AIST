"""Read-only market intelligence debug routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, Query

from app.deps import get_alpaca_news_service, get_analyst_data_service
from app.services.alpaca_news_service import AlpacaNewsService
from app.services.analyst_data_service import AnalystDataService

router = APIRouter(tags=["market-intelligence"])


@router.get("/market-news/{symbol}")
def market_news(
    symbol: str = Path(..., min_length=1, max_length=12),
    limit: int = Query(default=10, ge=1, le=50),
    news: AlpacaNewsService = Depends(get_alpaca_news_service),
) -> dict[str, Any]:
    """Read-only Alpaca news for debugging. Never executes trades."""
    return news.get_news_for_symbol(symbol, limit=limit)


@router.get("/analyst-data/{symbol}")
def analyst_data(
    symbol: str = Path(..., min_length=1, max_length=12),
    analyst: AnalystDataService = Depends(get_analyst_data_service),
) -> dict[str, Any]:
    """Read-only analyst data for debugging. Never executes trades."""
    return analyst.get_analyst_consensus(symbol)
