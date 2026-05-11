from datetime import datetime, timezone

from pydantic import BaseModel, Field


class LessonModel(BaseModel):
    trade_id: str
    symbol: str
    was_successful: bool
    lesson: str
    improvement_suggestion: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
