from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.agent_model import AgentResultModel
from app.models.cycle_model import BotCycleResultModel
from app.models.decision_model import DecisionModel
from app.models.lesson_model import LessonModel


class BotStartResponse(BaseModel):
    status: Literal["started"] = "started"
    message: str = Field(default="Demo bot cycle completed")


class BotStopResponse(BaseModel):
    status: Literal["stopped"] = "stopped"


class BotTickStoppedResponse(BaseModel):
    status: Literal["stopped"] = "stopped"
    message: str


class BotStatusResponse(BaseModel):
    status: Literal["started", "stopped"]
    open_trades_count: int
    history_count: int
    decisions_count: int
    execution_mode: Literal["PAPER_DEMO", "BINANCE_TESTNET"] = "BINANCE_TESTNET"
    has_open_position: bool = False
    open_position_symbol: str | None = None
    open_position_source: str | None = None
    open_position_pnl: float | None = None
    open_position_pnl_percent: float | None = None
    open_position_cycles: int | None = None
    last_open_skipped_reason: str | None = Field(
        default=None,
        description="Why the last cycle did not open a trade (null if it opened).",
    )


class ForceCloseResponse(BaseModel):
    status: Literal["closed", "noop"]
    message: str
    closed_trade_ids: list[str] = Field(default_factory=list)


class DecisionsListResponse(BaseModel):
    decisions: list[DecisionModel]


class AgentsLatestResponse(BaseModel):
    agents: list[AgentResultModel]


class TeamChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)


class TeamChatReply(BaseModel):
    agent_id: str
    agent_name: str
    role: str
    answer: str
    detail: str
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    veto: bool = False


class TeamChatResponse(BaseModel):
    user_message: str
    provider_status: dict
    replies: list[TeamChatReply]


class LessonsListResponse(BaseModel):
    lessons: list[LessonModel]


class BotTickOkResponse(BaseModel):
    """Cycle payload when the bot is running."""

    cycle: BotCycleResultModel


class ForceDemoTradeRequest(BaseModel):
    """Optional symbol for UI-only forced demo open (paper)."""

    symbol: str | None = Field(
        default=None,
        description="BTCUSDT or ETHUSDT; default picks first available slot.",
    )


class ExecutionModeResponse(BaseModel):
    mode: Literal["PAPER_DEMO", "BINANCE_TESTNET"]


class ExecutionModeSetRequest(BaseModel):
    mode: Literal["PAPER_DEMO", "BINANCE_TESTNET"]


class TestnetTrackedOrderRow(BaseModel):
    """Serialized bot-tracked Spot Testnet order attempt/result."""

    symbol: str
    side: str
    order_id: int
    status: str
    executed_qty: float
    cumulative_quote_qty: float
    avg_price: float | None = None
    created_at: datetime
    client_tag: str = ""
    error_message: str | None = None


class TestnetOrdersResponse(BaseModel):
    orders: list[TestnetTrackedOrderRow]
    warning: str = Field(
        default="Binance Spot Testnet only — not mainnet. Bot-tracked rows only.",
    )


class ForceDemoTradeResponse(BaseModel):
    """Result of POST /bot/force-demo-trade (no exchange orders)."""

    opened_trade_id: str | None = None
    attempted_symbol: str
    open_skipped_reason: str | None = None
    message: str = Field(
        default="",
        description="Human-readable outcome for UI debugging.",
    )
