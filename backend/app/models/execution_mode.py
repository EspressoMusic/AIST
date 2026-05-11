"""Bot execution mode - demo/paper brokers only, never mainnet."""

from enum import Enum


class ExecutionMode(str, Enum):
    PAPER_DEMO = "PAPER_DEMO"
    BINANCE_TESTNET = "BINANCE_TESTNET"
    ALPACA_PAPER = "ALPACA_PAPER"
