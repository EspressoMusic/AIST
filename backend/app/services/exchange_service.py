"""Exchange-facing price quotes: live public Binance tickers with safe fallback."""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings, get_settings
from app.models.market_model import MarketPricesResponse
from app.services.binance_testnet_service import BinanceTestnetService

logger = logging.getLogger(__name__)

_FALLBACK_BTC = 65000.0
_FALLBACK_ETH = 3200.0
_AI_TEAM_WATCHED_FALLBACKS: dict[str, dict[str, float]] = {
    "BTCUSDT": {
        "latest_price": _FALLBACK_BTC,
        "price_change_percent_24h": 0.35,
        "volume": 12000.0,
        "quote_volume": 780000000.0,
    },
    "ETHUSDT": {
        "latest_price": _FALLBACK_ETH,
        "price_change_percent_24h": 0.18,
        "volume": 85000.0,
        "quote_volume": 272000000.0,
    },
    "SOLUSDT": {
        "latest_price": 150.0,
        "price_change_percent_24h": 0.55,
        "volume": 2500000.0,
        "quote_volume": 375000000.0,
    },
    "BNBUSDT": {
        "latest_price": 620.0,
        "price_change_percent_24h": -0.1,
        "volume": 400000.0,
        "quote_volume": 248000000.0,
    },
}


class ExchangeService:
    def __init__(
        self,
        binance: BinanceTestnetService | None = None,
        settings: Settings | None = None,
    ) -> None:
        settings = settings or get_settings()
        self._binance = binance or BinanceTestnetService(settings)

    def get_prices(self) -> MarketPricesResponse:
        """Try Binance public tickers; on any failure return fixed dummy prices."""
        symbols = ["BTCUSDT", "ETHUSDT"]
        try:
            prices = self._binance.get_live_prices(symbols)
            btc = prices.get("BTCUSDT")
            eth = prices.get("ETHUSDT")
            if btc is None or eth is None:
                raise ValueError("Incomplete symbol map from Binance")
            return MarketPricesResponse(
                BTCUSDT=btc,
                ETHUSDT=eth,
                source="binance_public",
            )
        except Exception as exc:
            logger.warning("Using fallback dummy prices: %s", exc)
            return MarketPricesResponse(
                BTCUSDT=_FALLBACK_BTC,
                ETHUSDT=_FALLBACK_ETH,
                source="fallback_dummy",
            )

    def get_asset_market_snapshot(self, symbols: list[str]) -> dict[str, Any]:
        """
        Real public Binance 24h market snapshot for AI Team previews.

        This is read-only and never executes trades. If Binance public data fails,
        return a deterministic mock snapshot marked ``MOCK``.
        """
        watched = [s.strip().upper() for s in symbols if s.strip()]
        try:
            raw = self._binance.get_public_24h_tickers(watched)
            if not raw:
                raise RuntimeError("Empty Binance 24h ticker snapshot")
            assets: dict[str, dict[str, Any]] = {}
            for symbol in watched:
                row = raw.get(symbol)
                if row is None:
                    continue
                latest = float(row.get("latest_price") or 0.0)
                change_pct = float(row.get("price_change_percent_24h") or 0.0)
                assets[symbol] = {
                    "symbol": symbol,
                    "latest_price": latest,
                    "recent_price_movement_pct": change_pct,
                    "price_change_percent_24h": change_pct,
                    "volume": float(row.get("volume") or 0.0),
                    "quote_volume": float(row.get("quote_volume") or 0.0),
                    "high_price": float(row.get("high_price") or 0.0),
                    "low_price": float(row.get("low_price") or 0.0),
                    "open_price": float(row.get("open_price") or 0.0),
                }
            if len(assets) != len(watched):
                raise RuntimeError("Incomplete Binance 24h ticker snapshot")
            return {
                "current_status": "REAL_DATA",
                "data_sources": ["binance_public_24h_ticker"],
                "assets": assets,
                "error": None,
            }
        except Exception as exc:
            logger.warning("Using AI team mock market snapshot: %s", exc)
            assets = {}
            for symbol in watched:
                fallback = dict(_AI_TEAM_WATCHED_FALLBACKS.get(symbol, {}))
                latest = float(fallback.get("latest_price") or 1.0)
                change_pct = float(fallback.get("price_change_percent_24h") or 0.0)
                assets[symbol] = {
                    "symbol": symbol,
                    "latest_price": latest,
                    "recent_price_movement_pct": change_pct,
                    "price_change_percent_24h": change_pct,
                    "volume": float(fallback.get("volume") or 0.0),
                    "quote_volume": float(fallback.get("quote_volume") or 0.0),
                    "high_price": latest * 1.01,
                    "low_price": latest * 0.99,
                    "open_price": latest / (1.0 + change_pct / 100.0)
                    if change_pct != -100
                    else latest,
                }
            return {
                "current_status": "MOCK",
                "data_sources": ["mock_asset_market_snapshot"],
                "assets": assets,
                "error": str(exc),
            }

    def get_technical_klines_snapshot(
        self,
        symbol: str,
        *,
        interval: str = "15m",
        limit: int = 120,
    ) -> dict[str, Any]:
        """
        Read-only public Binance klines for AI Team technical analysis.

        If public kline fetch fails, return deterministic mock candles and mark
        the snapshot as ``MOCK``.
        """
        sym = symbol.strip().upper()
        try:
            klines = self._binance.get_public_klines(sym, interval=interval, limit=limit)
            candles = [_normalize_kline(row) for row in klines]
            if len(candles) < 30:
                raise RuntimeError("Not enough public kline candles")
            return {
                "current_status": "REAL_DATA",
                "data_sources": ["binance_public_klines"],
                "symbol": sym,
                "interval": interval,
                "candles": candles,
                "error": None,
            }
        except Exception as exc:
            logger.warning("Using AI team mock klines for %s: %s", sym, exc)
            return {
                "current_status": "MOCK",
                "data_sources": ["mock_technical_klines"],
                "symbol": sym,
                "interval": interval,
                "candles": _mock_candles(sym, limit),
                "error": str(exc),
            }


def _normalize_kline(row: list[Any]) -> dict[str, float]:
    return {
        "open_time": float(row[0]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": float(row[5]),
    }


def _mock_candles(symbol: str, limit: int) -> list[dict[str, float]]:
    base = {
        "BTCUSDT": _FALLBACK_BTC,
        "ETHUSDT": _FALLBACK_ETH,
        "SOLUSDT": 150.0,
        "BNBUSDT": 620.0,
    }.get(symbol, 100.0)
    candles: list[dict[str, float]] = []
    last = base
    for i in range(max(30, min(limit, 160))):
        drift = (i - limit / 2.0) * base * 0.000015
        wave = base * 0.0015 * (1 if i % 7 < 4 else -1)
        close = max(base * 0.5, last + drift + wave)
        high = max(last, close) * 1.001
        low = min(last, close) * 0.999
        candles.append(
            {
                "open_time": float(i),
                "open": round(last, 8),
                "high": round(high, 8),
                "low": round(low, 8),
                "close": round(close, 8),
                "volume": 1000.0 + i * 5.0,
            },
        )
        last = close
    return candles
