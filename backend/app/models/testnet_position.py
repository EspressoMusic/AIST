"""Single-slot Spot Testnet position tracked by the bot (max one open)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestnetTrackedPosition:
    symbol: str
    base_quantity: float
    quote_spent: float
    entry_order_id: int
    opened_at: datetime
    demo_trade_id: str
