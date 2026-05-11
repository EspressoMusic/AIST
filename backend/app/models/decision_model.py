from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class DecisionModel(BaseModel):
    symbol: str
    final_action: str = Field(description="BUY | SELL | HOLD")
    confidence: float
    news_score: float
    technical_score: float
    risk_score: float
    risk_approved: bool
    explanation: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    # BINANCE_TESTNET BUY path: scoring + gates (None for paper or non-gated paths).
    testnet_entry: dict[str, Any] | None = Field(
        default=None,
        description="Testnet strategy engine diagnostics when a BUY is evaluated.",
    )
    # Multi-agent brain snapshot (mock logic; ready for LLM providers later).
    brain: dict[str, Any] | None = Field(
        default=None,
        description="Per-agent outputs, debate result, execution gate diagnostics.",
    )
    final_confidence: float | None = Field(
        default=None,
        description="Same as confidence when produced by debate agent; optional duplicate for APIs.",
    )
    final_reasons: list[str] | None = Field(
        default=None,
        description="Bullet reasons from the debate / brain layer.",
    )
