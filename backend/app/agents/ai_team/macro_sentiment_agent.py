"""Macro & Sentiment Agent."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.agents.ai_team.base_agent import AgentResponse, AiTeamContext, BaseAiTeamAgent
from app.services.alpaca_news_service import AlpacaNewsService
from app.services.analyst_data_service import AnalystDataService
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
        alpaca_news: AlpacaNewsService | None = None,
        analyst_data: AnalystDataService | None = None,
    ) -> None:
        self._news_data = news_data
        self._ai = ai_provider
        self._alpaca_news = alpaca_news
        self._analyst_data = analyst_data

    def analyze(self, context: AiTeamContext) -> AgentResponse:
        if context.execution_mode == "ALPACA_PAPER":
            return self._analyze_alpaca_paper(context)
        if self._news_data is not None:
            return self._analyze_real_news(context)
        return self._mock_response(context, "News data service is not configured.")

    def _analyze_alpaca_paper(self, context: AiTeamContext) -> AgentResponse:
        news_bundle = (
            self._alpaca_news.get_news_for_symbol(context.symbol, limit=10)
            if self._alpaca_news is not None
            else {
                "ok": False,
                "configured": False,
                "message": "Alpaca news service is not configured.",
                "news_items": [],
                "data_sources": [],
            }
        )
        analyst = (
            self._analyst_data.get_analyst_consensus(context.symbol)
            if self._analyst_data is not None
            else _disabled_analyst_summary(context.symbol, "Analyst data service is not configured.")
        )
        news_items = list(news_bundle.get("news_items") or [])
        news_ok = bool(news_bundle.get("ok")) and bool(news_items)
        analyst_ok = bool(analyst.get("configured")) and bool(analyst.get("raw_available"))
        data_sources: list[str] = []
        if news_ok:
            data_sources.append("alpaca_news")
        if analyst_ok:
            data_sources.append("fmp_analyst_data")

        if news_ok and analyst_ok:
            current_status = "REAL_DATA"
        elif news_ok or analyst_ok:
            current_status = "PARTIAL_REAL_DATA"
        else:
            current_status = "MOCK"

        if current_status == "MOCK":
            return self.response(
                action="HOLD",
                confidence=0.0,
                risk_level="MEDIUM",
                veto=False,
                short_reason="No real macro data available",
                reason=(
                    "Alpaca news and analyst data were unavailable, so Macro/Sentiment "
                    "falls back to neutral HOLD."
                ),
                data_used=_macro_data_used(
                    context=context,
                    current_status=current_status,
                    news_items=[],
                    analyst=analyst,
                    data_sources=[],
                    sentiment_score=0.0,
                    news_sentiment="NEUTRAL",
                    action="HOLD",
                    reason=str(news_bundle.get("message") or analyst.get("message") or "No real data."),
                ),
            )

        heuristic = _heuristic_sentiment(news_items, str(analyst.get("consensus") or "UNKNOWN"))
        ai_advice = None
        ai_connected = False
        if self._ai is not None and self._ai.active_provider != "MOCK":
            ai_advice = self._ai.analyze_market_sentiment(
                _stock_macro_prompt(context.symbol, news_items, analyst),
            )
            ai_status = self._ai.status()
            ai_connected = (
                ai_status.get("last_used_provider") != "MOCK"
                and ai_status.get("last_error") is None
            )
            if ai_connected:
                data_sources.append(f"{str(ai_status.get('last_used_provider')).lower()}_summary")

        if ai_connected and ai_advice is not None:
            news_sentiment = str(ai_advice.get("market_bias") or heuristic["news_sentiment"]).upper()
            sentiment_score = float(ai_advice.get("sentiment_score") or 0.0) / 100.0
            action = str(ai_advice.get("action") or "HOLD").upper()
            confidence = float(ai_advice.get("confidence") or 0.0)
            risk_level = str(ai_advice.get("risk_level") or "MEDIUM").upper()
            short_reason = str(ai_advice.get("short_reason") or "AI summarized macro data")
            reason = str(ai_advice.get("reason") or short_reason)
        else:
            news_sentiment = str(heuristic["news_sentiment"])
            sentiment_score = float(heuristic["sentiment_score"])
            action = str(heuristic["action"])
            confidence = float(heuristic["confidence"])
            risk_level = str(heuristic["risk_level"])
            short_reason = str(heuristic["short_reason"])
            reason = str(heuristic["reason"])

        analyst_bias = str(analyst.get("consensus") or "UNKNOWN").upper()
        if news_sentiment == "BEARISH" and confidence >= 65:
            action = "SELL" if sentiment_score <= -0.65 else "HOLD"
            risk_level = "HIGH"
            short_reason = "Bearish news blocks BUY"
        if analyst_bias == "BEARISH" and action == "BUY":
            action = "HOLD"
            confidence = min(confidence, 64.0)
            short_reason = "Analyst bias prevents BUY"

        return self.response(
            action=action,  # type: ignore[arg-type]
            confidence=confidence,
            risk_level=risk_level,  # type: ignore[arg-type]
            veto=False,
            short_reason=short_reason,
            reason=reason,
            data_used=_macro_data_used(
                context=context,
                current_status=current_status,
                news_items=news_items,
                analyst=analyst,
                data_sources=data_sources,
                sentiment_score=sentiment_score,
                news_sentiment=news_sentiment,
                action=action,
                reason=reason,
            ),
        )

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


def _stock_macro_prompt(
    symbol: str,
    news_items: list[Any],
    analyst: dict[str, Any],
) -> str:
    compact_news = [
        {
            "headline": item.get("headline"),
            "source": item.get("source"),
            "published_at": item.get("published_at"),
            "summary": item.get("summary"),
        }
        for item in news_items[:10]
        if isinstance(item, dict)
    ]
    return (
        "Analyze stock market news and analyst data for a paper-only trading advisor. "
        "Do not execute trades. Return strict JSON with market_bias, sentiment_score "
        "(-100 bearish to +100 bullish), action, confidence, risk_level, short_reason, "
        "reason, veto. If data is mixed or weak, prefer HOLD. If news is strongly "
        "bearish, do not return BUY. "
        f"Symbol={symbol}. News={json.dumps(compact_news, ensure_ascii=False)}. "
        f"Analyst={json.dumps(analyst, ensure_ascii=False)}"
    )


def _macro_data_used(
    *,
    context: AiTeamContext,
    current_status: str,
    news_items: list[Any],
    analyst: dict[str, Any],
    data_sources: list[str],
    sentiment_score: float,
    news_sentiment: str,
    action: str,
    reason: str,
) -> dict[str, Any]:
    top_news = [
        {
            "headline": item.get("headline"),
            "summary": item.get("summary"),
            "url": item.get("url"),
            "source": item.get("source"),
            "published_at": item.get("published_at"),
            "symbols": item.get("symbols", []),
        }
        for item in news_items[:5]
        if isinstance(item, dict)
    ]
    analyst_bias = str(analyst.get("consensus") or "UNKNOWN").upper()
    return {
        "current_status": current_status,
        "symbol": context.symbol,
        "sentiment_score": round(max(-1.0, min(1.0, sentiment_score)), 4),
        "market_bias": news_sentiment,
        "news_sentiment": news_sentiment,
        "analyst_bias": analyst_bias,
        "news_items_count": len(news_items),
        "news_items": news_items,
        "top_news": top_news,
        "analyst_summary": analyst,
        "data_sources": data_sources,
        "action": action,
        "reason": reason,
        "economic_calendar": "not_connected",
        "central_bank_inflation_rates": "not_connected",
        "analyst_sentiment": analyst_bias,
    }


def _heuristic_sentiment(news_items: list[Any], analyst_bias: str) -> dict[str, Any]:
    positive = {
        "beat",
        "beats",
        "upgrade",
        "upgraded",
        "raises",
        "raised",
        "growth",
        "record",
        "surge",
        "rally",
        "bullish",
        "strong",
    }
    negative = {
        "miss",
        "misses",
        "downgrade",
        "downgraded",
        "cuts",
        "cut",
        "lawsuit",
        "probe",
        "weak",
        "bearish",
        "falls",
        "slump",
        "warning",
    }
    score = 0
    for item in news_items[:10]:
        if not isinstance(item, dict):
            continue
        text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
        score += sum(1 for word in positive if word in text)
        score -= sum(1 for word in negative if word in text)
    analyst = analyst_bias.upper()
    if analyst == "BULLISH":
        score += 2
    elif analyst == "BEARISH":
        score -= 2
    normalized = max(-1.0, min(1.0, score / 6.0))
    if normalized >= 0.35:
        return {
            "news_sentiment": "BULLISH",
            "sentiment_score": normalized,
            "action": "BUY",
            "confidence": min(72.0, 52.0 + normalized * 30.0),
            "risk_level": "MEDIUM",
            "short_reason": "News and analyst tone lean bullish",
            "reason": "Real news/analyst data lean bullish, but this remains advisory only.",
        }
    if normalized <= -0.35:
        return {
            "news_sentiment": "BEARISH",
            "sentiment_score": normalized,
            "action": "SELL",
            "confidence": min(78.0, 52.0 + abs(normalized) * 34.0),
            "risk_level": "HIGH",
            "short_reason": "News and analyst tone are bearish",
            "reason": "Real news/analyst data lean bearish; Macro will not support BUY.",
        }
    return {
        "news_sentiment": "NEUTRAL",
        "sentiment_score": normalized,
        "action": "HOLD",
        "confidence": 56.0,
        "risk_level": "MEDIUM",
        "short_reason": "Macro tone is neutral",
        "reason": "Real news/analyst data are mixed or not decisive; HOLD is safer.",
    }


def _disabled_analyst_summary(symbol: str, message: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "provider": "FMP",
        "configured": False,
        "status": "DISABLED",
        "price_target": {
            "target_high": None,
            "target_low": None,
            "target_consensus": None,
            "target_median": None,
        },
        "ratings": {
            "buy": None,
            "hold": None,
            "sell": None,
            "strong_buy": None,
            "strong_sell": None,
        },
        "consensus": "UNKNOWN",
        "raw_available": False,
        "message": message,
    }


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
