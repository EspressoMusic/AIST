"""Live mark-to-market for open Binance Spot Testnet demo trades (public ticker)."""

from __future__ import annotations

import logging

from app.demo_bot_constants import TRADE_SOURCE_BINANCE_TESTNET
from app.models.demo_trade import DemoTrade, demo_unrealized_pnl
from app.services.binance_testnet_service import BinanceTestnetService

logger = logging.getLogger(__name__)


def refresh_binance_testnet_open_trade_mtm(
    trade: DemoTrade,
    binance: BinanceTestnetService,
) -> None:
    """Set ``current_price`` from Testnet last price and refresh ``profit_loss`` (unrealized)."""
    if not trade.is_open or (trade.source or "") != TRADE_SOURCE_BINANCE_TESTNET:
        return
    try:
        trade.current_price = float(binance.get_testnet_last_price(trade.symbol))
        trade.profit_loss = float(demo_unrealized_pnl(trade))
    except Exception as exc:
        logger.warning(
            "get_testnet_last_price failed for %s (open trade %s): %s",
            trade.symbol,
            trade.id,
            exc,
        )
