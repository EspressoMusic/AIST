"""Shared primitives for the 4-agent AI trading team.

This module is advisory-only. Agents return structured recommendations; they do
not execute trades or bypass the existing execution gate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentAction = Literal["BUY", "SELL", "HOLD"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
AgentStatus = Literal["REAL_DATA", "PARTIAL_REAL_DATA", "MOCK", "AI_CONNECTED"]


class AiTeamContext(BaseModel):
    symbol: str
    watched_symbols: list[str]
    prices: dict[str, float]
    current_price: float
    open_positions: int
    daily_loss: float
    trade_count_today: int
    consecutive_losses: int
    decisions_count: int
    execution_mode: str
    data_source: str
    asset_market_data: dict[str, dict[str, Any]] = Field(default_factory=dict)
    asset_data_sources: list[str] = Field(default_factory=list)
    asset_current_status: AgentStatus = "MOCK"
    asset_fallback_reason: Any | None = None
    technical_candles: list[dict[str, Any]] = Field(default_factory=list)
    technical_data_sources: list[str] = Field(default_factory=list)
    technical_current_status: AgentStatus = "MOCK"
    technical_fallback_reason: Any | None = None
    risk_snapshot: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent_name: str
    role: str
    action: AgentAction
    confidence: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    veto: bool
    short_reason: str
    reason: str
    data_used: dict[str, Any] = Field(default_factory=dict)
    current_status: AgentStatus = "MOCK"
    trade_allowed: bool | None = None
    position_size: float | None = None
    risk_checks: dict[str, Any] | None = None
    sentiment_score: float | None = None
    news_sentiment: str | None = None
    analyst_bias: str | None = None
    news_items_count: int | None = None
    top_news: list[dict[str, Any]] | None = None
    analyst_summary: dict[str, Any] | None = None
    data_sources: list[str] | None = None


class BaseAiTeamAgent(ABC):
    agent_name: str
    role: str

    @abstractmethod
    def analyze(self, context: AiTeamContext) -> AgentResponse:
        """Return one structured advisory response."""

    def response(
        self,
        *,
        action: AgentAction,
        confidence: float,
        risk_level: RiskLevel,
        veto: bool,
        short_reason: str,
        reason: str,
        data_used: dict[str, Any],
        current_status: AgentStatus = "MOCK",
        trade_allowed: bool | None = None,
        position_size: float | None = None,
        risk_checks: dict[str, Any] | None = None,
    ) -> AgentResponse:
        inferred_status = data_used.get("current_status")
        if current_status == "MOCK" and inferred_status in {
            "REAL_DATA",
            "PARTIAL_REAL_DATA",
            "MOCK",
            "AI_CONNECTED",
        }:
            current_status = inferred_status  # type: ignore[assignment]
        return AgentResponse(
            agent_name=self.agent_name,
            role=self.role,
            action=action,
            confidence=round(max(0.0, min(100.0, confidence)), 2),
            risk_level=risk_level,
            veto=veto,
            short_reason=short_reason,
            reason=reason,
            data_used=data_used,
            current_status=current_status,
            trade_allowed=trade_allowed,
            position_size=position_size,
            risk_checks=risk_checks,
            sentiment_score=data_used.get("sentiment_score"),
            news_sentiment=data_used.get("news_sentiment") or data_used.get("market_bias"),
            analyst_bias=data_used.get("analyst_bias"),
            news_items_count=data_used.get("news_items_count"),
            top_news=data_used.get("top_news"),
            analyst_summary=data_used.get("analyst_summary"),
            data_sources=data_used.get("data_sources"),
        )
