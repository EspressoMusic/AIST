"""Alpaca Paper Trading client.

This service is restricted to Alpaca's paper endpoint. It is not wired into the
bot engine and must never be pointed at Alpaca live trading.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings

_REQUEST_TIMEOUT_SEC = 15.0
_PAPER_HOST = "paper-api.alpaca.markets"
_STOCK_FALLBACKS: dict[str, dict[str, float]] = {
    "AAPL": {"latest_price": 190.0, "price_change_percent_24h": 0.25, "volume": 52000000.0},
    "TSLA": {"latest_price": 185.0, "price_change_percent_24h": -0.45, "volume": 93000000.0},
    "NVDA": {"latest_price": 900.0, "price_change_percent_24h": 0.85, "volume": 42000000.0},
    "SPY": {"latest_price": 525.0, "price_change_percent_24h": 0.18, "volume": 71000000.0},
    "QQQ": {"latest_price": 445.0, "price_change_percent_24h": 0.38, "volume": 51000000.0},
}


class AlpacaPaperService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.alpaca_paper_api_key.strip()
            and self._settings.alpaca_paper_api_secret.strip()
        )

    @property
    def is_paper_endpoint(self) -> bool:
        parsed = urlparse(self._paper_base_url())
        return parsed.scheme == "https" and parsed.netloc == _PAPER_HOST

    def get_status(self) -> dict[str, Any]:
        return {
            "configured": self.is_configured,
            "paper_trading_only": True,
            "live_trading_allowed": False,
            "paper_endpoint_ok": self.is_paper_endpoint,
            "base_url": self._paper_base_url(),
            "data_base_url": self._data_base_url(),
        }

    def get_account(self) -> dict[str, Any]:
        data = self._request_trading("GET", "/v2/account")
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Alpaca account response shape")
        return data

    def get_positions(self) -> list[dict[str, Any]]:
        data = self._request_trading("GET", "/v2/positions")
        if not isinstance(data, list):
            raise RuntimeError("Unexpected Alpaca positions response shape")
        return [dict(row) for row in data if isinstance(row, dict)]

    def get_latest_price(self, symbol: str) -> dict[str, Any]:
        sym = self._clean_symbol(symbol)
        try:
            trade = self._request_data(
                "GET",
                f"/v2/stocks/{sym}/trades/latest",
                params={"feed": "iex"},
            )
            if isinstance(trade, dict):
                price = _nested_number(trade, "trade", "p")
                if price is not None:
                    return {
                        "symbol": sym,
                        "price": price,
                        "source": "alpaca_latest_trade",
                        "raw": trade,
                    }
        except Exception:
            # Some accounts/data plans may not have latest trades; try quote next.
            pass
        quote = self._request_data(
            "GET",
            f"/v2/stocks/{sym}/quotes/latest",
            params={"feed": "iex"},
        )
        if not isinstance(quote, dict):
            raise RuntimeError("Unexpected Alpaca quote response shape")
        ask = _nested_number(quote, "quote", "ap")
        bid = _nested_number(quote, "quote", "bp")
        price = ask or bid
        if ask and bid:
            price = (ask + bid) / 2.0
        if price is None:
            raise RuntimeError(f"Missing Alpaca latest price for {sym}")
        return {
            "symbol": sym,
            "price": price,
            "source": "alpaca_latest_quote",
            "raw": quote,
        }

    def get_stock_bars(
        self,
        symbol: str,
        *,
        timeframe: str = "15Min",
        limit: int = 120,
    ) -> list[dict[str, Any]]:
        sym = self._clean_symbol(symbol)
        lim = max(30, min(int(limit), 1000))
        start = _bars_start_iso(timeframe=timeframe, limit=lim)
        data = self._request_data(
            "GET",
            f"/v2/stocks/{sym}/bars",
            params={
                "timeframe": timeframe,
                "start": start,
                "limit": str(lim),
                "feed": "iex",
                "sort": "asc",
            },
        )
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Alpaca bars response shape")
        bars = data.get("bars")
        if not isinstance(bars, list):
            raise RuntimeError(f"Missing Alpaca bars for {sym}")
        return [dict(row) for row in bars if isinstance(row, dict)]

    def get_stock_market_snapshot(self, symbols: list[str]) -> dict[str, Any]:
        watched = [self._clean_symbol(symbol) for symbol in symbols if symbol.strip()]
        try:
            self._ensure_ready()
        except Exception as exc:
            return {
                "current_status": "MOCK",
                "data_sources": ["mock_alpaca_stock_market_snapshot"],
                "assets": _mock_stock_market_assets(watched, fallback_reason=str(exc)),
                "error": str(exc),
            }

        assets: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}
        real_symbols = 0
        bars_symbols = 0
        for symbol in watched:
            try:
                latest = self.get_latest_price(symbol)
                latest_price = float(latest.get("price") or 0.0)
                try:
                    bars = self.get_stock_bars(symbol, timeframe="1Hour", limit=48)
                    bars_symbols += 1
                except Exception as bars_exc:
                    bars = []
                    errors[symbol] = f"bars unavailable: {bars_exc}"
                assets[symbol] = _stock_snapshot_from_bars(
                    symbol,
                    latest_price=latest_price,
                    bars=bars,
                    source="alpaca_latest_price",
                    fallback_reason=errors.get(symbol),
                )
                assets[symbol]["price_source"] = str(latest.get("source") or "alpaca_latest_price")
                real_symbols += 1
            except Exception as exc:
                errors[symbol] = str(exc)
                assets[symbol] = _mock_stock_market_assets(
                    [symbol],
                    fallback_reason=str(exc),
                )[symbol]

        if real_symbols == len(watched) and bars_symbols == len(watched):
            status = "REAL_DATA"
        elif real_symbols > 0:
            status = "PARTIAL_REAL_DATA"
        else:
            status = "MOCK"
        data_sources = (
            ["alpaca_market_snapshot", "alpaca_latest_price", "alpaca_stock_bars"]
            if bars_symbols > 0
            else ["alpaca_market_snapshot", "alpaca_latest_price"]
            if real_symbols > 0
            else ["mock_alpaca_stock_market_snapshot"]
        )
        return {
            "current_status": status,
            "data_sources": data_sources,
            "assets": assets,
            "error": None if not errors else errors,
        }

    def get_stock_bars_snapshot(
        self,
        symbol: str,
        *,
        timeframe: str = "15Min",
        limit: int = 120,
    ) -> dict[str, Any]:
        sym = self._clean_symbol(symbol)
        try:
            bars = self.get_stock_bars(sym, timeframe=timeframe, limit=limit)
            candles = [_normalize_alpaca_bar(row, i) for i, row in enumerate(bars)]
            if len(candles) < 30:
                raise RuntimeError("Not enough Alpaca stock candles")
            return {
                "current_status": "REAL_DATA",
                "data_sources": ["alpaca_stock_bars"],
                "symbol": sym,
                "interval": timeframe,
                "candles": candles,
                "error": None,
            }
        except Exception as exc:
            return {
                "current_status": "MOCK",
                "data_sources": ["mock_alpaca_stock_bars"],
                "symbol": sym,
                "interval": timeframe,
                "candles": _mock_stock_bars(sym, limit),
                "error": str(exc),
            }

    def place_market_buy(self, symbol: str, notional_amount: float) -> dict[str, Any]:
        amount = float(notional_amount)
        if amount <= 0:
            raise ValueError("notional_amount must be positive")
        return self._place_order(
            symbol=symbol,
            side="buy",
            payload={"notional": _fmt(amount)},
        )

    def place_market_sell(self, symbol: str, quantity: float) -> dict[str, Any]:
        qty = float(quantity)
        if qty <= 0:
            raise ValueError("quantity must be positive")
        return self._place_order(
            symbol=symbol,
            side="sell",
            payload={"qty": _fmt(qty)},
        )

    def close_position(self, symbol: str) -> dict[str, Any]:
        sym = self._clean_symbol(symbol)
        data = self._request_trading("DELETE", f"/v2/positions/{sym}")
        return dict(data) if isinstance(data, dict) else {"result": data}

    def _place_order(
        self,
        *,
        symbol: str,
        side: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        sym = self._clean_symbol(symbol)
        data = self._request_trading(
            "POST",
            "/v2/orders",
            json={
                "symbol": sym,
                "side": side,
                "type": "market",
                "time_in_force": "day",
                **payload,
            },
        )
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected Alpaca order response shape")
        return data

    def _request_trading(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        self._ensure_ready()
        with httpx.Client(timeout=httpx.Timeout(_REQUEST_TIMEOUT_SEC)) as client:
            response = client.request(
                method,
                f"{self._paper_base_url()}{path}",
                headers=self._headers(),
                json=json,
            )
        return self._handle_response(response)

    def _request_data(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        self._ensure_ready()
        with httpx.Client(timeout=httpx.Timeout(_REQUEST_TIMEOUT_SEC)) as client:
            response = client.request(
                method,
                f"{self._data_base_url()}{path}",
                headers=self._headers(),
                params=params or {},
            )
        return self._handle_response(response)

    def _ensure_ready(self) -> None:
        if not self.is_paper_endpoint:
            raise RuntimeError(
                "Alpaca live endpoint is not allowed. Use https://paper-api.alpaca.markets.",
            )
        if not self.is_configured:
            raise RuntimeError("Alpaca Paper API key/secret not configured.")

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._settings.alpaca_paper_api_key.strip(),
            "APCA-API-SECRET-KEY": self._settings.alpaca_paper_api_secret.strip(),
            "Content-Type": "application/json",
        }

    def _paper_base_url(self) -> str:
        return self._settings.alpaca_paper_base_url.strip().rstrip("/")

    def _data_base_url(self) -> str:
        return self._settings.alpaca_data_base_url.strip().rstrip("/")

    def _handle_response(self, response: httpx.Response) -> Any:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail: Any = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(str(detail)) from exc
        if not response.content:
            return {}
        return response.json()

    def _clean_symbol(self, symbol: str) -> str:
        sym = symbol.strip().upper()
        if not sym:
            raise ValueError("symbol is required")
        return sym


def _fmt(value: float) -> str:
    return f"{value:.12f}".rstrip("0").rstrip(".")


def _nested_number(payload: dict[str, Any], outer: str, inner: str) -> float | None:
    row = payload.get(outer)
    if not isinstance(row, dict):
        return None
    value = row.get(inner)
    if value is None:
        return None
    return float(value)


def _stock_snapshot_from_bars(
    symbol: str,
    *,
    latest_price: float,
    bars: list[dict[str, Any]],
    source: str,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    if not bars:
        fallback = _STOCK_FALLBACKS.get(symbol, {"latest_price": latest_price or 100.0})
        bars = _mock_stock_bars(symbol, 30, base=float(fallback.get("latest_price") or 100.0))
    first_open = float(bars[0].get("o") or bars[0].get("open") or latest_price or 0.0)
    closes = [float(row.get("c") or row.get("close") or 0.0) for row in bars]
    highs = [float(row.get("h") or row.get("high") or 0.0) for row in bars]
    lows = [float(row.get("l") or row.get("low") or 0.0) for row in bars]
    volumes = [float(row.get("v") or row.get("volume") or 0.0) for row in bars]
    close_basis = latest_price or (closes[-1] if closes else first_open)
    change_pct = (
        (close_basis - first_open) / first_open * 100.0
        if first_open > 0
        else 0.0
    )
    volume = sum(volumes)
    return {
        "symbol": symbol,
        "latest_price": round(close_basis, 8),
        "recent_price_movement_pct": round(change_pct, 4),
        "price_change_percent_24h": round(change_pct, 4),
        "volume": round(volume, 4),
        "quote_volume": round(volume * close_basis, 4),
        "high_price": round(max(highs) if highs else close_basis, 8),
        "low_price": round(min(lows) if lows else close_basis, 8),
        "open_price": round(first_open, 8),
        "source": source,
        "fallback_reason": fallback_reason,
    }


def _normalize_alpaca_bar(row: dict[str, Any], index: int) -> dict[str, float]:
    return {
        "open_time": float(index),
        "open": float(row.get("o") or row.get("open") or 0.0),
        "high": float(row.get("h") or row.get("high") or 0.0),
        "low": float(row.get("l") or row.get("low") or 0.0),
        "close": float(row.get("c") or row.get("close") or 0.0),
        "volume": float(row.get("v") or row.get("volume") or 0.0),
    }


def _mock_stock_market_assets(
    symbols: list[str],
    *,
    fallback_reason: str | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        symbol: _stock_snapshot_from_bars(
            symbol,
            latest_price=float(
                _STOCK_FALLBACKS.get(symbol, {}).get("latest_price") or 100.0,
            ),
            bars=_mock_stock_bars(symbol, 48),
            source="mock_stock_price",
            fallback_reason=fallback_reason,
        )
        for symbol in symbols
    }


def _bars_start_iso(*, timeframe: str, limit: int) -> str:
    tf = timeframe.lower()
    if "hour" in tf:
        lookback = timedelta(days=max(10, int(limit / 6) + 4))
    elif "day" in tf:
        lookback = timedelta(days=max(60, limit * 2))
    else:
        lookback = timedelta(days=max(10, int(limit / 20) + 6))
    return (datetime.now(timezone.utc) - lookback).isoformat().replace("+00:00", "Z")


def _mock_stock_bars(
    symbol: str,
    limit: int,
    *,
    base: float | None = None,
) -> list[dict[str, float]]:
    fallback = _STOCK_FALLBACKS.get(symbol, {})
    base_price = float(base or fallback.get("latest_price") or 100.0)
    direction = float(fallback.get("price_change_percent_24h") or 0.0) / 100.0
    candles: list[dict[str, float]] = []
    last = base_price * (1.0 - direction)
    count = max(30, min(limit, 180))
    for i in range(count):
        progress = (i + 1) / count
        drift = base_price * direction * progress / max(count / 12.0, 1.0)
        wave = base_price * 0.0018 * (1 if i % 8 < 4 else -1)
        close = max(base_price * 0.25, last + drift + wave)
        high = max(last, close) * 1.0015
        low = min(last, close) * 0.9985
        candles.append(
            {
                "open_time": float(i),
                "open": round(last, 8),
                "high": round(high, 8),
                "low": round(low, 8),
                "close": round(close, 8),
                "volume": round(float(fallback.get("volume") or 1000000.0) / count, 4),
            },
        )
        last = close
    return candles
