"""Alpaca Paper Trading client.

This service is restricted to Alpaca's paper endpoint. It is not wired into the
bot engine and must never be pointed at Alpaca live trading.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings

_REQUEST_TIMEOUT_SEC = 15.0
_PAPER_HOST = "paper-api.alpaca.markets"


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
