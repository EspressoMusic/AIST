"""Symbol-aware news data service for AI Team macro analysis."""

from __future__ import annotations

from typing import Any

from app.services.news_source_service import NewsSourceService

_ASSET_NAMES = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana",
    "BNBUSDT": "BNB",
}


class NewsDataService:
    def __init__(self, source: NewsSourceService) -> None:
        self._source = source

    def asset_name_for_symbol(self, symbol: str) -> str:
        sym = symbol.strip().upper()
        return _ASSET_NAMES.get(sym, sym.replace("USDT", ""))

    def fetch_symbol_news(self, symbol: str) -> dict[str, Any]:
        sym = symbol.strip().upper()
        asset_name = self.asset_name_for_symbol(sym)
        items = self._source.fetch(sym)
        status = self._source.status()
        provider = str(status.get("last_provider_used") or status.get("configured_provider") or "MOCK")
        current_status = "MOCK" if provider == "MOCK" else "REAL_DATA"
        data_sources = [provider]
        connected_apis = [] if provider == "MOCK" else [provider]
        return {
            "symbol": sym,
            "asset_name": asset_name,
            "current_status": current_status,
            "data_sources": data_sources,
            "connected_apis": connected_apis,
            "news_source_status": status,
            "news_items": [item.model_dump() for item in items],
        }
