"""In-memory demo trade (not an exchange order)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.demo_bot_constants import DEMO_TRADE_NOTIONAL_USD


@dataclass
class DemoTrade:
    id: str
    symbol: str
    side: str  # "Buy" | "Sell"
    entry_price: float
    current_price: float
    quantity: float
    profit_loss: float
    opened_at: datetime
    closed_at: datetime | None = None
    is_open: bool = True
    reason: str = ""
    demo_cycles_open: int = 0
    source: str = "PAPER_DEMO"
    binance_order_id: int | None = None
    sell_order_id: int | None = None
    # Closed-trade bookkeeping (OPEN trades leave exit_price / sell_quote_proceeds unset).
    exit_price: float | None = None
    buy_quote_cost: float | None = None  # BINANCE_TESTNET: BUY cumulativeQuoteQty (USDT spent).
    sell_quote_proceeds: float | None = None  # BINANCE_TESTNET: SELL cumulative quote received.


def demo_effective_quantity(trade: DemoTrade) -> float:
    if trade.quantity and trade.quantity > 0:
        return trade.quantity
    if trade.entry_price > 0:
        return DEMO_TRADE_NOTIONAL_USD / trade.entry_price
    return 0.0


def demo_unrealized_pnl(trade: DemoTrade) -> float:
    """Mark-to-market P/L in quote currency (notional * price delta)."""
    q = demo_effective_quantity(trade)
    entry = trade.entry_price
    cur = trade.current_price
    if entry <= 0 or q <= 0:
        return 0.0
    if trade.side.lower() == "buy":
        return (cur - entry) * q
    return (entry - cur) * q


def demo_pnl_fraction(trade: DemoTrade) -> float:
    if trade.entry_price <= 0:
        return 0.0
    if trade.side.lower() == "buy":
        return (trade.current_price - trade.entry_price) / trade.entry_price
    return (trade.entry_price - trade.current_price) / trade.entry_price


def demo_realized_pnl_at_close(trade: DemoTrade, *, exit_price: float) -> float:
    """Realized P/L in quote currency using exit vs entry (not raw sell proceeds alone)."""
    q = demo_effective_quantity(trade)
    entry = trade.entry_price
    if entry <= 0 or q <= 0:
        return 0.0
    if trade.side.lower() == "buy":
        return (exit_price - entry) * q
    return (entry - exit_price) * q


def closed_trade_realized_pl(trade: DemoTrade) -> float:
    """Single source of truth for CLOSED trade contribution to portfolio realized P/L."""
    buy_cq = trade.buy_quote_cost
    sell_cq = trade.sell_quote_proceeds
    if buy_cq is not None and sell_cq is not None:
        # Quote totals win for BINANCE_TESTNET (exchange-fill economics).
        return float(sell_cq) - float(buy_cq)
    if trade.exit_price is not None:
        return demo_realized_pnl_at_close(trade, exit_price=trade.exit_price)
    return float(trade.profit_loss or 0.0)
