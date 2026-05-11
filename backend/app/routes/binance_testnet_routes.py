"""Binance Spot Testnet smoke/trade-test routes — **not** wired to the demo bot engine."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.deps import get_binance_testnet_service
from app.services.binance_testnet_service import BinanceTestnetService

router = APIRouter(prefix="/binance-testnet", tags=["binance-testnet"])

_DISCLAIMER = (
    "Binance Spot Testnet only — not mainnet. Test funds only. "
    "The paper bot engine does not call these endpoints."
)


def require_binance_testnet_ready(
    settings: Settings = Depends(get_settings),
    svc: BinanceTestnetService = Depends(get_binance_testnet_service),
) -> BinanceTestnetService:
    if not settings.use_binance_testnet:
        raise HTTPException(
            status_code=503,
            detail=(
                "Binance Spot Testnet routes are disabled. "
                "Set USE_BINANCE_TESTNET=true in backend/.env."
            ),
        )
    if not svc.is_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Missing BINANCE_TESTNET_API_KEY or BINANCE_TESTNET_API_SECRET "
                "in backend/.env."
            ),
        )
    return svc


BinanceReady = Annotated[BinanceTestnetService, Depends(require_binance_testnet_ready)]


class TestnetMarketBuyBody(BaseModel):
    symbol: str = Field(..., min_length=4)
    quote_amount: float = Field(
        ...,
        gt=0,
        description="Quote notional for MARKET BUY (quoteOrderQty), e.g. USDT on BTCUSDT.",
    )


class TestnetMarketSellBody(BaseModel):
    symbol: str = Field(..., min_length=4)
    quantity: float = Field(..., gt=0, description="Base asset amount to sell.")


def _public_meta() -> dict[str, str]:
    return {
        "binance_environment": "spot_testnet",
        "warning": _DISCLAIMER,
    }


def _signed_meta() -> dict[str, str]:
    return {
        "binance_environment": "spot_testnet",
        "warning": _DISCLAIMER,
    }


def _order_meta() -> dict[str, str]:
    return {
        "binance_environment": "spot_testnet",
        "warning": _DISCLAIMER + " This submits a **testnet** market order.",
    }


@router.get("/ping")
def binance_testnet_ping(
    svc: BinanceTestnetService = Depends(get_binance_testnet_service),
) -> dict[str, Any]:
    """Unsigned connectivity check against ``BINANCE_TESTNET_BASE_URL``."""
    try:
        body = svc.ping()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_public_meta(), **body}


@router.get("/time")
def binance_testnet_time(
    svc: BinanceTestnetService = Depends(get_binance_testnet_service),
) -> dict[str, Any]:
    """Unsigned server time from Spot Testnet."""
    try:
        data = svc.get_server_time()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_public_meta(), "server_time": data}


@router.get("/account")
def binance_testnet_account(svc: BinanceReady) -> dict[str, Any]:
    try:
        account = svc.get_account()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_signed_meta(), "account": account}


@router.get("/balances")
def binance_testnet_balances(svc: BinanceReady) -> dict[str, Any]:
    try:
        balances = svc.get_balances()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_signed_meta(), "balances": balances}


@router.post("/test-buy")
def binance_testnet_test_buy(
    body: TestnetMarketBuyBody,
    svc: BinanceReady,
) -> dict[str, Any]:
    """**Testnet MARKET BUY** using ``quoteOrderQty`` — not connected to the demo bot."""
    try:
        order = svc.place_market_buy(body.symbol, body.quote_amount)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_order_meta(), "order": order}


@router.post("/test-sell")
def binance_testnet_test_sell(
    body: TestnetMarketSellBody,
    svc: BinanceReady,
) -> dict[str, Any]:
    """**Testnet MARKET SELL** — not connected to the demo bot."""
    try:
        order = svc.place_market_sell(body.symbol, body.quantity)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**_order_meta(), "order": order}
