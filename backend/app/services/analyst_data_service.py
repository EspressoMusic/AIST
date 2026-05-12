"""Optional analyst data provider for Alpaca Paper stock demos."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings

_REQUEST_TIMEOUT_SEC = 15.0
_FMP_ROOT = "https://financialmodelingprep.com"


class AnalystDataService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def provider(self) -> str:
        return (self._settings.analyst_provider or "FMP").strip().upper()

    @property
    def is_configured(self) -> bool:
        return self.provider == "FMP" and bool(self._settings.fmp_api_key.strip())

    def get_status(self, *, probe_symbol: str = "AAPL") -> dict[str, Any]:
        if self.provider != "FMP":
            return {
                "provider": self.provider,
                "configured": False,
                "ok": False,
                "message": "Unsupported analyst provider",
            }
        if not self.is_configured:
            return {
                "provider": "FMP",
                "configured": False,
                "ok": False,
                "message": "FMP_API_KEY not configured",
            }
        result = self.get_analyst_consensus(probe_symbol)
        return {
            "provider": "FMP",
            "configured": True,
            "ok": bool(result.get("raw_available")),
            "message": str(result.get("message") or "ok"),
        }

    def get_price_target(self, symbol: str) -> dict[str, Any]:
        return self.get_analyst_consensus(symbol).get("price_target", {})

    def get_analyst_ratings(self, symbol: str) -> dict[str, Any]:
        return self.get_analyst_consensus(symbol).get("ratings", {})

    def get_analyst_consensus(self, symbol: str) -> dict[str, Any]:
        sym = symbol.strip().upper()
        if self.provider != "FMP":
            return _disabled(sym, self.provider, "Unsupported analyst provider")
        if not self.is_configured:
            return _disabled(sym, "FMP", "FMP_API_KEY not configured")

        messages: list[str] = []
        price_target: dict[str, Any] = _empty_price_target()
        ratings: dict[str, Any] = _empty_ratings()
        raw_available = False

        try:
            target_rows = self._get_json(
                "/api/v4/price-target-consensus",
                {"symbol": sym},
            )
            target = target_rows[0] if isinstance(target_rows, list) and target_rows else target_rows
            if isinstance(target, dict):
                price_target = _normalize_price_target(target)
                raw_available = True
        except Exception as exc:
            messages.append(f"price target failed: {exc}")

        try:
            rating_rows = self._get_json(
                f"/api/v3/analyst-stock-recommendations/{sym}",
                {},
            )
            rating = rating_rows[0] if isinstance(rating_rows, list) and rating_rows else rating_rows
            if isinstance(rating, dict):
                ratings = _normalize_ratings(rating)
                raw_available = True
        except Exception as exc:
            messages.append(f"ratings failed: {exc}")

        consensus = _consensus_from_ratings(ratings)
        if consensus == "UNKNOWN":
            consensus = _consensus_from_target(price_target)
        return {
            "symbol": sym,
            "provider": "FMP",
            "configured": True,
            "status": "REAL_DATA" if raw_available else "ERROR",
            "price_target": price_target,
            "ratings": ratings,
            "consensus": consensus,
            "raw_available": raw_available,
            "message": "ok" if not messages else "; ".join(messages),
        }

    def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        with httpx.Client(timeout=httpx.Timeout(_REQUEST_TIMEOUT_SEC)) as client:
            response = client.get(
                f"{_FMP_ROOT}{path}",
                params={**params, "apikey": self._settings.fmp_api_key.strip()},
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail: Any = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(str(detail)) from exc
        return response.json()


def _disabled(symbol: str, provider: str, message: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "provider": provider,
        "configured": False,
        "status": "DISABLED",
        "price_target": _empty_price_target(),
        "ratings": _empty_ratings(),
        "consensus": "UNKNOWN",
        "raw_available": False,
        "message": message,
    }


def _empty_price_target() -> dict[str, Any]:
    return {
        "target_high": None,
        "target_low": None,
        "target_consensus": None,
        "target_median": None,
    }


def _empty_ratings() -> dict[str, Any]:
    return {
        "buy": None,
        "hold": None,
        "sell": None,
        "strong_buy": None,
        "strong_sell": None,
    }


def _number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except Exception:
            continue
    return None


def _normalize_price_target(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_high": _number(row, "targetHigh", "target_high", "high"),
        "target_low": _number(row, "targetLow", "target_low", "low"),
        "target_consensus": _number(row, "targetConsensus", "target_consensus", "consensus"),
        "target_median": _number(row, "targetMedian", "target_median", "median"),
    }


def _normalize_ratings(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "buy": _number(row, "analystRatingsbuy", "buy"),
        "hold": _number(row, "analystRatingsHold", "hold"),
        "sell": _number(row, "analystRatingsSell", "sell"),
        "strong_buy": _number(row, "analystRatingsStrongBuy", "strongBuy", "strong_buy"),
        "strong_sell": _number(row, "analystRatingsStrongSell", "strongSell", "strong_sell"),
    }


def _consensus_from_ratings(ratings: dict[str, Any]) -> str:
    bullish = float(ratings.get("buy") or 0) + float(ratings.get("strong_buy") or 0) * 1.5
    bearish = float(ratings.get("sell") or 0) + float(ratings.get("strong_sell") or 0) * 1.5
    hold = float(ratings.get("hold") or 0)
    total = bullish + bearish + hold
    if total <= 0:
        return "UNKNOWN"
    if bullish >= bearish * 1.5 and bullish >= hold:
        return "BULLISH"
    if bearish >= bullish * 1.5 and bearish >= hold:
        return "BEARISH"
    return "NEUTRAL"


def _consensus_from_target(price_target: dict[str, Any]) -> str:
    consensus = price_target.get("target_consensus")
    high = price_target.get("target_high")
    low = price_target.get("target_low")
    if consensus is None or high is None or low is None:
        return "UNKNOWN"
    try:
        target = float(consensus)
        midpoint = (float(high) + float(low)) / 2.0
    except Exception:
        return "UNKNOWN"
    if target > midpoint * 1.03:
        return "BULLISH"
    if target < midpoint * 0.97:
        return "BEARISH"
    return "NEUTRAL"
