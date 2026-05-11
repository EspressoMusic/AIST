"""Paper-only prices for demo marks: tiny jitter on venue quotes (never executed)."""

from __future__ import annotations

import hashlib

from app.demo_bot_constants import DEMO_TICK_PRICE_JITTER_MAX_FRAC
from app.models.market_model import MarketPricesResponse


def demo_display_price_map(
    prices: MarketPricesResponse,
    tick_seq: int,
) -> dict[str, float]:
    """Return symbol → price used for demo current_price / P/L display only."""
    out: dict[str, float] = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        raw = getattr(prices, symbol)
        j = _jitter_frac(symbol, tick_seq)
        out[symbol] = raw * (1.0 + j)
    return out


def _jitter_frac(symbol: str, tick_seq: int) -> float:
    if DEMO_TICK_PRICE_JITTER_MAX_FRAC <= 0:
        return 0.0
    payload = f"{symbol}:{tick_seq}".encode()
    h = hashlib.sha256(payload).digest()
    u = int.from_bytes(h[:4], "big") / (2**32 - 1)
    signed = u * 2.0 - 1.0
    return signed * DEMO_TICK_PRICE_JITTER_MAX_FRAC
