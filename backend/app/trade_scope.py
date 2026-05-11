"""Execution-mode ↔ trade source filtering (shared by /trades, /portfolio, /performance)."""

from __future__ import annotations

from app.demo_bot_constants import (
    TRADE_SOURCE_ALPACA_PAPER,
    TRADE_SOURCE_BINANCE_TESTNET,
    TRADE_SOURCE_PAPER_DEMO,
)
from app.models.demo_trade import DemoTrade
from app.models.execution_mode import ExecutionMode


def want_source_for_execution_mode(mode: ExecutionMode) -> str:
    if mode == ExecutionMode.BINANCE_TESTNET:
        return TRADE_SOURCE_BINANCE_TESTNET
    if mode == ExecutionMode.ALPACA_PAPER:
        return TRADE_SOURCE_ALPACA_PAPER
    return TRADE_SOURCE_PAPER_DEMO


def trade_matches_execution_source(trade: DemoTrade, want_source: str) -> bool:
    return (trade.source or TRADE_SOURCE_PAPER_DEMO) == want_source
