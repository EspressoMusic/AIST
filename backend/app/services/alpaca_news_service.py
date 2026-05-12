"""Read-only Alpaca Market Data News client for stock demo sentiment."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings

_REQUEST_TIMEOUT_SEC = 15.0


class AlpacaNewsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.alpaca_paper_api_key.strip()
            and self._settings.alpaca_paper_api_secret.strip()
        )

    def get_status(self, *, probe_symbol: str = "AAPL") -> dict[str, Any]:
        if not self.is_configured:
            return {
                "provider": "ALPACA_NEWS",
                "configured": False,
                "ok": False,
                "message": "ALPACA_PAPER_API_KEY/SECRET not configured",
            }
        result = self.get_news_for_symbol(probe_symbol, limit=1)
        return {
            "provider": "ALPACA_NEWS",
            "configured": True,
            "ok": bool(result.get("ok")),
            "message": str(result.get("message") or "ok"),
        }

    def get_news_for_symbol(self, symbol: str, limit: int = 10) -> dict[str, Any]:
        sym = symbol.strip().upper()
        if not sym:
            return self._error("UNKNOWN", "symbol is required", configured=self.is_configured)
        if not self.is_configured:
            return self._error(sym, "ALPACA_PAPER_API_KEY/SECRET not configured", configured=False)
        try:
            payload = self._request_news(sym, limit=limit)
            raw_news = payload.get("news") if isinstance(payload, dict) else None
            if not isinstance(raw_news, list):
                raise RuntimeError("Unexpected Alpaca news response shape")
            items = [_normalize_news_item(sym, row) for row in raw_news if isinstance(row, dict)]
            return {
                "symbol": sym,
                "provider": "ALPACA_NEWS",
                "configured": True,
                "ok": True,
                "status": "REAL_DATA",
                "message": f"Fetched {len(items)} Alpaca news item(s).",
                "news_items": items,
                "data_sources": ["alpaca_news"],
            }
        except Exception as exc:
            return self._error(sym, str(exc), configured=True)

    def _request_news(self, symbol: str, *, limit: int) -> dict[str, Any]:
        root = self._settings.alpaca_data_base_url.strip().rstrip("/")
        params = {
            "symbols": symbol,
            "limit": str(max(1, min(int(limit), 50))),
            "sort": "desc",
        }
        with httpx.Client(timeout=httpx.Timeout(_REQUEST_TIMEOUT_SEC)) as client:
            response = client.get(
                f"{root}/v1beta1/news",
                headers={
                    "APCA-API-KEY-ID": self._settings.alpaca_paper_api_key.strip(),
                    "APCA-API-SECRET-KEY": self._settings.alpaca_paper_api_secret.strip(),
                },
                params=params,
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail: Any = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(str(detail)) from exc
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Expected Alpaca news JSON object")
        return data

    def _error(self, symbol: str, message: str, *, configured: bool) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "provider": "ALPACA_NEWS",
            "configured": configured,
            "ok": False,
            "status": "ERROR" if configured else "DISABLED",
            "message": message,
            "news_items": [],
            "data_sources": [],
        }


def _normalize_news_item(symbol: str, row: dict[str, Any]) -> dict[str, Any]:
    symbols = row.get("symbols")
    return {
        "symbol": symbol,
        "headline": str(row.get("headline") or row.get("title") or ""),
        "summary": str(row.get("summary") or ""),
        "url": str(row.get("url") or ""),
        "source": str(row.get("source") or ""),
        "published_at": str(row.get("created_at") or row.get("updated_at") or ""),
        "symbols": list(symbols) if isinstance(symbols, list) else [],
    }
