from datetime import datetime



from pydantic import BaseModel, Field





class TradeResponse(BaseModel):

    """Legacy minimal trade shape (unused by new /trades bundle)."""



    id: str = Field(description="Trade identifier")

    symbol: str = Field(description="Trading pair symbol")

    side: str = Field(description="Order side, e.g. BUY or SELL")

    status: str = Field(description="OPEN or CLOSED")





class TradeDetailResponse(BaseModel):

    id: str

    symbol: str

    side: str

    status: str  # OPEN | CLOSED

    entry_price: float

    current_price: float

    profit_loss: float

    quantity: float = 0.0

    opened_at: datetime

    closed_at: datetime | None = None

    exit_price: float | None = None

    reason: str = ""

    source: str = "PAPER_DEMO"

    binance_order_id: int | None = None

    buy_order_id: int | None = None

    sell_order_id: int | None = None

    buy_cummulative_quote_qty: float | None = None

    sell_cummulative_quote_qty: float | None = None





class TradesBundleResponse(BaseModel):

    open_trades: list[TradeDetailResponse]

    history: list[TradeDetailResponse]


