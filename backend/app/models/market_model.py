from typing import Literal

from pydantic import BaseModel, Field


class MarketPricesResponse(BaseModel):
    """Spot-style symbol → last price map plus quote source."""

    BTCUSDT: float = Field(description="Last price for BTCUSDT")
    ETHUSDT: float = Field(description="Last price for ETHUSDT")
    source: Literal["binance_public", "fallback_dummy"] = Field(
        description="binance_public = live public ticker; fallback_dummy = offline placeholder",
    )
