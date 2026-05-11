from pydantic import BaseModel, Field


class PortfolioResponse(BaseModel):
    starting_balance: float = Field(..., description="Baseline capital for demo P/L")
    current_value: float = Field(..., description="Mark-to-market portfolio value")
    total_profit_loss: float = Field(..., description="current_value - starting_balance")
    change_percent: float = Field(
        ...,
        description="total_profit_loss / starting_balance * 100",
    )
    realized_profit_loss: float = Field(
        ...,
        description="Sum of profit_loss on closed (history) demo trades",
    )
    unrealized_profit_loss: float = Field(
        ...,
        description="Sum of profit_loss on open demo trades",
    )
    open_trades_count: int = Field(..., description="Number of open demo positions")
    closed_trades_count: int = Field(..., description="Number of closed demo trades in history")
