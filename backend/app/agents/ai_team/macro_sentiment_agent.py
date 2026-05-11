"""Macro & Sentiment Agent."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.agents.ai_team.base_agent import AgentResponse, AiTeamContext, BaseAiTeamAgent
from app.services.ai_provider_service import AIProviderService
from app.services.news_data_service import NewsDataService


class MacroSentimentAgent(BaseAiTeamAgent):
    agent_name = "Macro & Sentiment Agent"
    role = "Analyze news, macro events, and market sentiment."

    def __init__(
        self,
        *,
        news_data: NewsDataService | None = None,
        ai_provider: AIProviderService | None = None,
    ) -> None:
        self._news_data = news_data
        self._ai = ai_provider

    def analyze(self, context: AiTeamContext) -> AgentResponse:
        if self._news_data is not None:
            return self._analyze_real_news(context)
        return self._mock_response(context, "News data service is not configured.")

    def _analyze_real_news(self, context: AiTeamContext) -> AgentResponse:
        assert self._news_data is not None
        news_bundle = self._news_data.fetch_symbol_news(context.symbol)
        news_items = list(news_bundle.get("news_items") or [])
        if news_bundle.get("current_status") == "MOCK":
            return self._neutral_response(
                news_bundle,
                "News fetch failed or no real provider is configured; returning neutral HOLD.",
                current_status="MOCK",
                ai_advice=_neutral_ai_advice("News fetch failed; neutral HOLD fallback."),
            )

        ai_advice = _neutral_ai_advice("AI provider unavailable; neutral HOLD fallback.")
        ai_connected = False
        if self._ai is not None:
            ai_advice = self._ai.analyze_market_sentiment(
                _macro_prompt(context.symbol, str(news_bundle.get("asset_name")), news_items),
            )
            ai_status = self._ai.status()
            ai_connected = (
                ai_status.get("last_used_provider") != "MOCK"
                and ai_status.get("last_error") is None
            )

        if not ai_connected:
            return self._neutral_response(
                news_bundle,
                "Real news was fetched, but AI sentiment analysis used a fallback; returning neutral HOLD.",
                current_status="REAL_DATA",
                ai_advice=ai_advice,
            )

        action = str(ai_advice.get("action") or "HOLD").upper()
        confidence = float(ai_advice.get("confidence") or 0.0)
        risk_level = str(ai_advice.get("risk_level") or "MEDIUM").upper()
        short_reason = str(ai_advice.get("short_reason") or "AI sentiment analyzed")
        reason = str(ai_advice.get("reason") or short_reason)
        return self.response(
            action=action,  # type: ignore[arg-type]
            confidence=confidence,
            risk_level=risk_level,  # type: ignore[arg-type]
            veto=bool(ai_advice.get("veto")),
            short_reason=short_reason,
            reason=reason,
            data_used={
                "current_status": "AI_CONNECTED",
                "market_bias": ai_advice.get("market_bias", "NEUTRAL"),
                "sentiment_score": ai_advice.get("sentiment_score", 0.0),
                "data_sources": news_bundle.get("data_sources", []),
                "connected_apis": [
                    *list(news_bundle.get("connected_apis") or []),
                    self._ai.status().get("last_used_provider") if self._ai else None,
                ],
                "asset_name": news_bundle.get("asset_name"),
                "news_items": news_items,
                "ai_advice": ai_advice,
                "economic_calendar": "placeholder",
                "central_bank_inflation_rates": "placeholder",
                "analyst_sentiment": "placeholder",
            },
        )

    def _neutral_response(
        self,
        news_bundle: dict[str, Any],
        reason: str,
        *,
        current_status: str,
        ai_advice: dict[str, Any],
    ) -> AgentResponse:
        return self.response(
            action="HOLD",
            confidence=0.0,
            risk_level="MEDIUM",
            veto=False,
            short_reason="Neutral macro fallback",
            reason=reason,
            data_used={
                "current_status": current_status,
                "market_bias": "NEUTRAL",
                "sentiment_score": 0.0,
                "data_sources": news_bundle.get("data_sources", []),
                "connected_apis": news_bundle.get("connected_apis", []),
                "asset_name": news_bundle.get("asset_name"),
                "news_items": list(news_bundle.get("news_items") or []),
                "ai_advice": ai_advice,
                "economic_calendar": "placeholder",
                "central_bank_inflation_rates": "placeholder",
                "analyst_sentiment": "placeholder",
            },
        )

    def _mock_response(self, context: AiTeamContext, reason_prefix: str = "") -> AgentResponse:
        seed = int(hashlib.sha256(context.symbol.encode()).hexdigest()[:4], 16)
        sentiment_score = (seed % 41) - 20
        macro_pressure = ((seed // 7) % 31) - 15
        combined = sentiment_score * 0.65 + macro_pressure * 0.35

        if combined >= 8:
            action = "BUY"
            risk_level = "MEDIUM"
            short_reason = "Macro tone leans supportive"
        elif combined <= -8:
            action = "SELL"
            risk_level = "HIGH"
            short_reason = "Macro tone is cautious"
        else:
            action = "HOLD"
            risk_level = "MEDIUM"
            short_reason = "Macro signal is not decisive"

        confidence = min(88.0, 52.0 + abs(combined) * 1.7)
        reason = (
            f"{reason_prefix} Mock macro and sentiment foundation only. It reserves fields for "
            "economic calendar, news sentiment, central bank/inflation/rates, "
            "and analyst sentiment before connecting real APIs."
        ).strip()

        return self.response(
            action=action,  # type: ignore[arg-type]
            confidence=confidence,
            risk_level=risk_level,  # type: ignore[arg-type]
            veto=False,
            short_reason=short_reason,
            reason=reason,
            data_used={
                "economic_calendar": "placeholder",
                "news_sentiment": "placeholder",
                "central_bank_inflation_rates": "placeholder",
                "analyst_sentiment": "placeholder",
                "current_status": "MOCK",
                "data_sources": ["mock_macro_sentiment"],
                "connected_apis": [],
                "news_items": [],
                "ai_advice": _neutral_ai_advice("Mock macro fallback."),
                "mock_sentiment_score": round(sentiment_score, 2),
                "mock_macro_pressure": round(macro_pressure, 2),
                "combined_macro_score": round(combined, 2),
            },
        )


def _macro_prompt(symbol: str, asset_name: str, news_items: list[Any]) -> str:
    compact_items = [
        {
            "title": item.get("title"),
            "source": item.get("source"),
            "published_at": item.get("published_at"),
            "summary": item.get("summary"),
        }
        for item in news_items[:12]
        if isinstance(item, dict)
    ]
    return (
        "Analyze market/news sentiment for a crypto trading advisory agent. "
        "Do not execute trades. Return strict JSON only with market_bias, "
        "sentiment_score, action, confidence, risk_level, short_reason, reason, veto. "
        f"Symbol={symbol}. Asset={asset_name}. News items="
        f"{json.dumps(compact_items, ensure_ascii=False)}"
    )


def _neutral_ai_advice(reason: str) -> dict[str, Any]:
    return {
        "market_bias": "NEUTRAL",
        "sentiment_score": 0.0,
        "action": "HOLD",
        "confidence": 0.0,
        "risk_level": "MEDIUM",
        "short_reason": "Neutral sentiment fallback",
        "reason": reason,
        "veto": False,
    }
