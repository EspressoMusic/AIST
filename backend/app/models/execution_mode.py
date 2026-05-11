"""Bot execution mode — paper simulation vs Binance Spot Testnet (still no mainnet)."""

from enum import Enum


class ExecutionMode(str, Enum):
    PAPER_DEMO = "PAPER_DEMO"
    BINANCE_TESTNET = "BINANCE_TESTNET"
