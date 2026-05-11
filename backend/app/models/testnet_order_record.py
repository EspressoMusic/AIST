"""Tracked Spot Testnet orders placed by the bot (not general exchange history)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TestnetOrderRecord:
    symbol: str
    side: str
    order_id: int
    status: str
    executed_qty: float
    cumulative_quote_qty: float
    avg_price: float | None
    created_at: datetime
    client_tag: str = ""
    error_message: str | None = None
