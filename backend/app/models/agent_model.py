from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AgentResultModel(BaseModel):
    agent_name: str
    symbol: str
    status: str = Field(
        description="e.g. completed, rejected, analyzing",
    )
    score: float
    action: str | None = None
    confidence: float | None = None
    explanation: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    # Structured output for brain / UI (mock today; LLM JSON later).
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Agent-specific diagnostics (scores, reasons, votes).",
    )
