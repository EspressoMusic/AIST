"""Alpaca Paper Trading routes.

These endpoints use Alpaca Paper only. They are not wired into the bot engine
and must never point at Alpaca live trading.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_alpaca_paper_service
from app.services.alpaca_paper_service import AlpacaPaperService

router = APIRouter(prefix="/alpaca-paper", tags=["alpaca-paper"])

_WARNING = "Alpaca Paper only - not live trading. These routes are manual paper tests."


class AlpacaMarketBuyBody(BaseModel):
    symbol: str = Field(..., min_length=1)
    notional_amount: float = Field(..., gt=0)


class AlpacaMarketSellBody(BaseModel):
    symbol: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)


def require_alpaca_paper_ready(
    svc: AlpacaPaperService = Depends(get_alpaca_paper_service),
) -> AlpacaPaperService:
    status = svc.get_status()
    if not status.get("paper_endpoint_ok"):
        raise HTTPException(
            status_code=503,
            detail="Alpaca live endpoint is not allowed. Use paper-api.alpaca.markets.",
        )
    if not status.get("configured"):
        raise HTTPException(
            status_code=503,
            detail="Missing ALPACA_PAPER_API_KEY or ALPACA_PAPER_API_SECRET.",
        )
    return svc


AlpacaReady = Annotated[AlpacaPaperService, Depends(require_alpaca_paper_ready)]


def _meta() -> dict[str, Any]:
    return {
        "alpaca_environment": "paper",
        "paper_trading_only": True,
        "live_trading_allowed": False,
        "warning": _WARNING,
    }


@router.get("/status")
def alpaca_paper_status(
    svc: AlpacaPaperService = Depends(get_alpaca_paper_service),
) -> dict[str, Any]:
    return {**_meta(), **svc.get_status()}


@router.get("/account")
def alpaca_paper_account(svc: AlpacaReady) -> dict[str, Any]:
    try:
        account = svc.get_account()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_meta(), "account": account}


@router.get("/positions")
def alpaca_paper_positions(svc: AlpacaReady) -> dict[str, Any]:
    try:
        positions = svc.get_positions()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_meta(), "positions": positions}


@router.get("/latest-price/{symbol}")
def alpaca_paper_latest_price(symbol: str, svc: AlpacaReady) -> dict[str, Any]:
    try:
        latest = svc.get_latest_price(symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_meta(), "latest_price": latest}


@router.post("/test-buy")
def alpaca_paper_test_buy(body: AlpacaMarketBuyBody, svc: AlpacaReady) -> dict[str, Any]:
    try:
        order = svc.place_market_buy(body.symbol, body.notional_amount)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_meta(), "order": order}


@router.post("/test-sell")
def alpaca_paper_test_sell(body: AlpacaMarketSellBody, svc: AlpacaReady) -> dict[str, Any]:
    try:
        order = svc.place_market_sell(body.symbol, body.quantity)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_meta(), "order": order}
