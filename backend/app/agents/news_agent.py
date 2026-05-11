"""News & sentiment agent with real provider support and safe mock fallback."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from app.models.agent_model import AgentResultModel

_BULLISH_TERMS = (
    "surge",
    "rally",
    "inflow",
    "approval",
    "record",
    "adoption",
    "bull",
    "beats",
    "partnership",
)
_BEARISH_TERMS = (
    "hack",
    "lawsuit",
    "outflow",
    "ban",
    "probe",
    "fraud",
    "bear",
    "misses",
    "selloff",
    "liquidation",
)


def analyze(
    symbol: str,
    *,
    seed_hint: float | None = None,
    ai_client: Any | None = None,
    news_source: Any | None = None,
) -> AgentResultModel:
    news_items = []
    news_status: dict[str, Any] = {"configured_provider": "MOCK"}
    if news_source is not None:
        news_items = list(news_source.fetch(symbol))
        news_status = news_source.status()

    rng = random.Random(int(hash(symbol + str(seed_hint or 0)) % (2**32)))
    score = _headline_score(news_items)
    if not news_items:
        score = rng.uniform(-22.0, 22.0)
    if score > 5.0:
        sentiment: str = "bullish"
    elif score < -5.0:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    impact = round(min(1.0, abs(score) / 22.0), 3)
    headline_rows = [_news_item_payload(item) for item in news_items]
    reasons = (
        [
            f"Scanned {len(news_items)} real/news-source headline(s) for {symbol}.",
            f"Provider={news_status.get('last_provider_used') or news_status.get('configured_provider')}.",
            f"Keyword sentiment={sentiment} raw_score={score:.1f}.",
        ]
        if news_items
        else [
            f"Mock headline flow for {symbol} (seeded).",
            f"Sentiment={sentiment} raw_score={score:.1f}.",
            "Configure NEWS_PROVIDER + API key in backend/.env for real headlines.",
        ]
    )

    payload: dict[str, Any] = {
        "provider": news_status.get("last_provider_used") or "mock_headlines",
        "news_source_status": news_status,
        "sentiment": sentiment,
        "impact_score": impact,
        "raw_score": round(score, 2),
        "news_items": headline_rows,
        "headlines": [row["title"] for row in headline_rows],
        "reasons": reasons,
        "api_ready": {
            "providers": "CRYPTOPANIC, FINNHUB, NEWSAPI, RSS",
            "auth": "keys in backend/.env only",
        },
    }
    if ai_client is not None:
        payload["ai_advice"] = ai_client.analyze_with_ai(
            (
                "News and sentiment interpretation only. Do not execute trades. "
                f"Symbol={symbol}. Provider status={news_status}. "
                f"Keyword sentiment={sentiment}. Impact={impact}. "
                f"Scanned headlines={headline_rows}. Reasons={reasons}"
            ),
            None,
        )
        payload["ai_provider"] = ai_client.status()
        ai_action = str(payload["ai_advice"].get("action") or "HOLD").upper()
        ai_conf = float(payload["ai_advice"].get("confidence") or 0.0)
        if ai_action == "BUY":
            score = max(score, min(22.0, ai_conf / 100.0 * 22.0))
            sentiment = "bullish"
        elif ai_action == "SELL":
            score = min(score, -min(22.0, ai_conf / 100.0 * 22.0))
            sentiment = "bearish"
        else:
            score *= 0.55
            sentiment = "neutral" if abs(score) <= 5 else sentiment
        impact = round(min(1.0, abs(score) / 22.0), 3)
        payload["sentiment"] = sentiment
        payload["impact_score"] = impact
        payload["raw_score"] = round(score, 2)

    bias = "supportive" if score >= 0 else "cautious"
    source_label = "news-source" if news_items else "mock"
    return AgentResultModel(
        agent_name="News & Sentiment Agent",
        symbol=symbol,
        status="completed",
        score=round(score, 2),
        action=None,
        confidence=round(min(abs(score) + 35.0, 98.0), 2),
        explanation=f"{source_label} {sentiment} narrative ({bias}) — impact {impact:.2f}.",
        created_at=datetime.now(timezone.utc),
        payload=payload,
    )


def _headline_score(items: list[Any]) -> float:
    if not items:
        return 0.0
    score = 0.0
    for item in items:
        blob = f"{getattr(item, 'title', '')} {getattr(item, 'summary', '')}".lower()
        score += sum(3.5 for term in _BULLISH_TERMS if term in blob)
        score -= sum(4.0 for term in _BEARISH_TERMS if term in blob)
    return max(-22.0, min(22.0, score))


def _news_item_payload(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if isinstance(item, dict):
        return dict(item)
    return {
        "title": str(getattr(item, "title", "")),
        "source": str(getattr(item, "source", "")),
        "url": str(getattr(item, "url", "")),
        "published_at": str(getattr(item, "published_at", "")),
        "summary": str(getattr(item, "summary", "")),
    }
