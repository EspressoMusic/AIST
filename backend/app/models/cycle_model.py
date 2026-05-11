from pydantic import BaseModel, Field

from app.models.agent_model import AgentResultModel
from app.models.decision_model import DecisionModel


class BotCycleResultModel(BaseModel):
    """Single demo decision cycle output (no exchange orders)."""

    decision: DecisionModel
    agents: list[AgentResultModel] = Field(
        default_factory=list,
        description="Market, Technical, News, Risk, Learning, Debate, Execution Gate, Execution.",
    )
    attempted_symbol: str = Field(
        description="Symbol evaluated this cycle (paper selection).",
    )
    intended_action: str = Field(
        description="Debate agent proposed side (BUY | SELL | HOLD) before execution gates.",
    )
    opened_trade_id: str | None = None
    closed_trade_ids: list[str] = Field(default_factory=list)
    open_skipped_reason: str | None = Field(
        default=None,
        description="Why a demo trade was not opened this cycle (paper gates).",
    )
