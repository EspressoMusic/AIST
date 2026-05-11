"""Configurable news sources for the News Agent.

Providers are read-only. They never execute trades and they never receive API
keys from Flutter; all keys stay in backend/.env.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import Settings


@dataclass(frozen=True)
class NewsItem:
    title: str
    source: str
    url: str
    published_at: str
    summary: str = ""

    def model_dump(self) -> dict[str, str]:
        return asdict(self)


class NewsSourceService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._last_error: str | None = None
        self._last_provider_used = "MOCK"

    def status(self) -> dict[str, Any]:
        return {
            "configured_provider": self.provider,
            "last_provider_used": self._last_provider_used,
            "last_error": self._last_error,
            "max_items": self.max_items,
            "lookback_hours": self._settings.news_lookback_hours,
        }

    @property
    def provider(self) -> str:
        raw = (self._settings.news_provider or "MOCK").strip().upper()
        if raw in {"CRYPTOPANIC", "FINNHUB", "NEWSAPI", "RSS"}:
            return raw
        return "MOCK"

    @property
    def max_items(self) -> int:
        return max(1, min(30, int(self._settings.news_max_items or 12)))

    def fetch(self, symbol: str) -> list[NewsItem]:
        provider = self.provider
        try:
            if provider == "CRYPTOPANIC":
                items = self._fetch_cryptopanic(symbol)
            elif provider == "FINNHUB":
                items = self._fetch_finnhub(symbol)
            elif provider == "NEWSAPI":
                items = self._fetch_newsapi(symbol)
            elif provider == "RSS":
                items = self._fetch_rss(symbol)
            else:
                items = self._mock_items(symbol)
                provider = "MOCK"
            self._last_provider_used = provider
            self._last_error = None
            return items[: self.max_items]
        except Exception as exc:
            self._last_provider_used = "MOCK"
            self._last_error = str(exc)
            return self._mock_items(symbol)

    def _fetch_cryptopanic(self, symbol: str) -> list[NewsItem]:
        key = self._settings.cryptopanic_api_key.strip()
        if not key:
            raise RuntimeError("CRYPTOPANIC_API_KEY is missing")
        currency = _symbol_currency(symbol)
        params = {
            "auth_token": key,
            "public": "true",
            "kind": "news",
            "filter": "hot",
        }
        if currency:
            params["currencies"] = currency
        url = "https://cryptopanic.com/api/developer/v2/posts/?" + urllib.parse.urlencode(params)
        payload = _url_json(url)
        results = payload.get("results")
        if not isinstance(results, list):
            return []
        out: list[NewsItem] = []
        for row in results:
            if not isinstance(row, dict):
                continue
            source = row.get("source")
            domain = row.get("domain")
            if not domain and isinstance(source, dict):
                domain = source.get("title")
            out.append(
                NewsItem(
                    title=str(row.get("title") or ""),
                    source=str(domain or "CryptoPanic"),
                    url=str(row.get("url") or ""),
                    published_at=str(row.get("published_at") or ""),
                    summary=str(row.get("metadata", {}).get("description") or "") if isinstance(row.get("metadata"), dict) else "",
                ),
            )
        return [item for item in out if item.title]

    def _fetch_finnhub(self, symbol: str) -> list[NewsItem]:
        key = self._settings.finnhub_api_key.strip()
        if not key:
            raise RuntimeError("FINNHUB_API_KEY is missing")
        sym = symbol.strip().upper().replace("USDT", "")
        if sym in {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE"}:
            url = f"https://finnhub.io/api/v1/news?category=crypto&token={urllib.parse.quote(key)}"
            rows = _url_json(url)
            terms = _symbol_terms(symbol)
            if isinstance(rows, list):
                return [
                    item
                    for item in (_finnhub_item(row) for row in rows)
                    if item is not None and _matches_terms(item, terms)
                ][: self.max_items]
            return []

        end = datetime.now(timezone.utc).date()
        start = end - timedelta(hours=max(1, self._settings.news_lookback_hours))
        params = urllib.parse.urlencode(
            {
                "symbol": sym,
                "from": start.isoformat(),
                "to": end.isoformat(),
                "token": key,
            },
        )
        rows = _url_json(f"https://finnhub.io/api/v1/company-news?{params}")
        if isinstance(rows, list):
            return [item for item in (_finnhub_item(row) for row in rows) if item is not None][
                : self.max_items
            ]
        return []

    def _fetch_newsapi(self, symbol: str) -> list[NewsItem]:
        key = self._settings.newsapi_api_key.strip()
        if not key:
            raise RuntimeError("NEWSAPI_API_KEY is missing")
        query = " OR ".join(_symbol_terms(symbol))
        params = urllib.parse.urlencode(
            {
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": str(self.max_items),
                "apiKey": key,
            },
        )
        payload = _url_json(f"https://newsapi.org/v2/everything?{params}")
        articles = payload.get("articles")
        if not isinstance(articles, list):
            return []
        out: list[NewsItem] = []
        for row in articles:
            if not isinstance(row, dict):
                continue
            source = row.get("source")
            out.append(
                NewsItem(
                    title=str(row.get("title") or ""),
                    source=str(source.get("name") if isinstance(source, dict) else "NewsAPI"),
                    url=str(row.get("url") or ""),
                    published_at=str(row.get("publishedAt") or ""),
                    summary=str(row.get("description") or ""),
                ),
            )
        return [item for item in out if item.title]

    def _fetch_rss(self, symbol: str) -> list[NewsItem]:
        urls = [u.strip() for u in self._settings.news_rss_urls.split(",") if u.strip()]
        if not urls:
            raise RuntimeError("NEWS_RSS_URLS is empty")
        terms = _symbol_terms(symbol)
        out: list[NewsItem] = []
        for feed_url in urls:
            root = ET.fromstring(_url_text(feed_url))
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                summary = (item.findtext("description") or "").strip()
                news = NewsItem(
                    title=title,
                    source=urllib.parse.urlparse(feed_url).netloc or "RSS",
                    url=(item.findtext("link") or "").strip(),
                    published_at=(item.findtext("pubDate") or "").strip(),
                    summary=summary,
                )
                if title and _matches_terms(news, terms):
                    out.append(news)
        return out[: self.max_items]

    def _mock_items(self, symbol: str) -> list[NewsItem]:
        sym = symbol.strip().upper()
        now = datetime.now(timezone.utc).isoformat()
        return [
            NewsItem(
                title=f"{sym} market flow remains mixed while traders wait for confirmation",
                source="Mock News",
                url="",
                published_at=now,
                summary="Fallback headline used until a real news API is configured.",
            ),
            NewsItem(
                title=f"Analysts watch volatility and ETF flows around {sym}",
                source="Mock News",
                url="",
                published_at=now,
                summary="Mock context for the News Agent and AI advisor.",
            ),
        ]


def _finnhub_item(row: object) -> NewsItem | None:
    if not isinstance(row, dict):
        return None
    ts = row.get("datetime")
    published = ""
    if isinstance(ts, (int, float)) and ts > 0:
        published = datetime.fromtimestamp(ts, timezone.utc).isoformat()
    return NewsItem(
        title=str(row.get("headline") or ""),
        source=str(row.get("source") or "Finnhub"),
        url=str(row.get("url") or ""),
        published_at=published,
        summary=str(row.get("summary") or ""),
    )


def _symbol_currency(symbol: str) -> str:
    sym = symbol.strip().upper()
    for suffix in ("USDT", "USD"):
        if sym.endswith(suffix):
            return sym[: -len(suffix)]
    return sym


def _symbol_terms(symbol: str) -> list[str]:
    currency = _symbol_currency(symbol)
    aliases = {
        "BTC": ["BTC", "Bitcoin"],
        "ETH": ["ETH", "Ethereum"],
        "SOL": ["SOL", "Solana"],
        "BNB": ["BNB", "Binance"],
        "XRP": ["XRP", "Ripple"],
    }
    return aliases.get(currency, [currency, symbol.strip().upper()])


def _matches_terms(item: NewsItem, terms: list[str]) -> bool:
    blob = f"{item.title} {item.summary}".lower()
    return any(term.lower() in blob for term in terms)


def _url_json(url: str) -> Any:
    return json.loads(_url_text(url))


def _url_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "TradingBotNewsAgent/1.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        return res.read().decode("utf-8", errors="replace")
