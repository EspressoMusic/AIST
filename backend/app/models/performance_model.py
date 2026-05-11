from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PerformanceTradeBrief(BaseModel):
    id: str
    symbol: str
    profit_loss: float
    closed_at: datetime | None = None


class SymbolPerformanceSummary(BaseModel):
    symbol: str
    total_trades: int = Field(ge=0)
    winning_trades: int = Field(ge=0)
    losing_trades: int = Field(ge=0)
    break_even_trades: int = Field(ge=0)
    total_realized_profit_loss: float
    gross_profit: float
    gross_loss: float


class PerformanceResponse(BaseModel):
    execution_mode: Literal["PAPER_DEMO", "BINANCE_TESTNET", "ALPACA_PAPER"]
    total_trades: int = Field(ge=0)
    winning_trades: int = Field(ge=0)
    losing_trades: int = Field(ge=0)
    break_even_trades: int = Field(ge=0)
    win_rate: float = Field(
        description="Percentage 0–100: winning_trades / total_trades when total_trades > 0, else 0.",
    )
    total_realized_profit_loss: float
    gross_profit: float = Field(description="Sum of strictly positive profit_loss values.")
    gross_loss: float = Field(
        description="Sum of strictly negative profit_loss values (negative number).",
    )
    average_profit: float | None = Field(
        default=None,
        description="Mean profit among winners; null if no winning trades.",
    )
    average_loss: float | None = Field(
        default=None,
        description="Mean profit_loss among losers (negative); null if no losing trades.",
    )
    average_trade_profit_loss: float | None = Field(
        default=None,
        description="total_realized_profit_loss / total_trades when total_trades > 0.",
    )
    best_trade: PerformanceTradeBrief | None = None
    worst_trade: PerformanceTradeBrief | None = None
    profit_factor: float | None = Field(
        default=None,
        description="gross_profit / abs(gross_loss); null when gross_loss is 0.",
    )
    symbols: list[SymbolPerformanceSummary] = Field(default_factory=list)
    max_drawdown: float = 0.0
    consecutive_losses: int = 0
    current_loss_streak: int = 0
    best_symbol: str | None = None
    worst_symbol: str | None = None
    average_hold_time: float | None = Field(
        default=None,
        description="Average hold time in seconds when opened_at and closed_at are available.",
    )
    last_10_trades_summary: list[dict[str, Any]] = Field(default_factory=list)
    recommendation_summary: str = ""
