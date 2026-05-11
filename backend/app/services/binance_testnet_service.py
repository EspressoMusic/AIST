"""
Binance helpers.

- **Public** spot prices: ``api.binance.com`` (no key) — used by ``get_live_prices``.
- **Spot Testnet** signed REST: ``binance_testnet_base_url`` — keys only from ``Settings`` / ``.env``.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

_PUBLIC_TICKER_PRICE_PATH = "/api/v3/ticker/price"
_PUBLIC_TICKER_24HR_PATH = "/api/v3/ticker/24hr"
_REQUEST_TIMEOUT_SEC = 10.0
_RECV_WINDOW_MS = 5000


class BinanceTestnetService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.binance_testnet_api_key.strip()
            and self._settings.binance_testnet_api_secret.strip()
        )

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(_REQUEST_TIMEOUT_SEC)

    def _testnet_rest_root(self) -> str:
        """e.g. ``https://testnet.binance.vision/api`` — paths are ``/v3/...``."""
        b = self._settings.binance_testnet_base_url.strip().rstrip("/")
        if b.endswith("/api"):
            return b
        return f"{b}/api"

    def _testnet_url(self, api_path: str) -> str:
        p = api_path if api_path.startswith("/") else f"/{api_path}"
        return f"{self._testnet_rest_root()}{p}"

    @staticmethod
    def _fmt_param(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            s = f"{value:.12f}".rstrip("0").rstrip(".")
            return s if s else "0"
        return str(value)

    def _sign_query(self, params: dict[str, Any]) -> str:
        secret = self._settings.binance_testnet_api_secret.strip()
        p: dict[str, str] = {
            k: self._fmt_param(v) for k, v in params.items() if v is not None
        }
        p["timestamp"] = str(int(time.time() * 1000))
        p["recvWindow"] = str(_RECV_WINDOW_MS)

        query = urlencode(sorted(p.items()))
        sig = hmac.new(
            secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{query}&signature={sig}"

    def _headers_signed(self) -> dict[str, str]:
        return {"X-MBX-APIKEY": self._settings.binance_testnet_api_key.strip()}

    def _handle_response(self, response: httpx.Response) -> Any:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail: Any
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            logger.warning("Binance testnet HTTP %s: %s", response.status_code, detail)
            raise RuntimeError(str(detail)) from exc
        if not response.content:
            return {}
        return response.json()

    def _request_public_testnet(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = self._testnet_url(path)
        with httpx.Client(timeout=self._timeout()) as client:
            r = client.request(method, url, params=params or {})
            return self._handle_response(r)

    def get_testnet_last_price(self, symbol: str) -> float:
        """Last price from Spot Testnet public ``GET /v3/ticker/price`` (no API key)."""
        sym = symbol.strip().upper()
        data = self._request_public_testnet(
            "GET",
            "/v3/ticker/price",
            params={"symbol": sym},
        )
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected testnet ticker shape for {sym}")
        raw = data.get("price")
        if raw is None:
            raise RuntimeError(f"Missing price in testnet ticker for {sym}")
        return float(raw)

    def get_klines_public(
        self,
        symbol: str,
        *,
        interval: str = "15m",
        limit: int = 120,
    ) -> list[list[Any]]:
        """Spot Testnet public ``GET /v3/klines`` — OHLCV for strategy indicators."""
        sym = symbol.strip().upper()
        lim = max(20, min(int(limit), 1000))
        data = self._request_public_testnet(
            "GET",
            "/v3/klines",
            params={"symbol": sym, "interval": interval.strip(), "limit": lim},
        )
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected klines shape for {sym}")
        return data

    def _request_signed(self, method: str, path: str, params: dict[str, Any]) -> Any:
        if not self.is_configured:
            raise RuntimeError("Binance testnet API key/secret not configured.")
        query = self._sign_query(params)
        url = f"{self._testnet_url(path)}?{query}"
        with httpx.Client(timeout=self._timeout()) as client:
            r = client.request(
                method,
                url,
                headers=self._headers_signed(),
            )
            return self._handle_response(r)

    # --- Unsigned testnet connectivity ---

    def ping(self) -> dict[str, Any]:
        """``GET /v3/ping`` on Spot Testnet."""
        self._request_public_testnet("GET", "/v3/ping")
        return {"ping": "ok"}

    def get_server_time(self) -> dict[str, Any]:
        """``GET /v3/time`` — server time in ms."""
        data = self._request_public_testnet("GET", "/v3/time")
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected /time response shape")
        return data

    # --- Signed account ---

    def get_account(self) -> dict[str, Any]:
        """``GET /v3/account`` (signed)."""
        data = self._request_signed("GET", "/v3/account", {})
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected /account response shape")
        return data

    def get_balances(self) -> list[dict[str, Any]]:
        """Non-zero balances from ``GET /v3/account``."""
        acc = self.get_account()
        raw = acc.get("balances")
        if not isinstance(raw, list):
            return []
        out: list[dict[str, Any]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            free = float(row.get("free", 0) or 0)
            locked = float(row.get("locked", 0) or 0)
            if free > 0 or locked > 0:
                out.append(row)
        return out

    def place_market_buy(self, symbol: str, quote_amount: float) -> dict[str, Any]:
        """MARKET BUY using ``quoteOrderQty`` ( spends quote asset, e.g. USDT )."""
        sym = symbol.strip().upper()
        data = self._request_signed(
            "POST",
            "/v3/order",
            {
                "symbol": sym,
                "side": "BUY",
                "type": "MARKET",
                "quoteOrderQty": quote_amount,
            },
        )
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected order response shape")
        return data

    def place_market_sell(self, symbol: str, quantity: float) -> dict[str, Any]:
        """MARKET SELL base ``quantity``."""
        sym = symbol.strip().upper()
        data = self._request_signed(
            "POST",
            "/v3/order",
            {
                "symbol": sym,
                "side": "SELL",
                "type": "MARKET",
                "quantity": quantity,
            },
        )
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected order response shape")
        return data

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """``GET /v3/order`` (signed)."""
        sym = symbol.strip().upper()
        data = self._request_signed(
            "GET",
            "/v3/order",
            {"symbol": sym, "orderId": order_id},
        )
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected getOrder response shape")
        return data

    # --- Public mainnet spot (no key) — unchanged ---

    def get_live_prices(self, symbols: list[str]) -> dict[str, float]:
        """
        Fetch last trade price per symbol from Binance **public** API.

        Endpoint (per symbol): ``GET /api/v3/ticker/price?symbol=BTCUSDT``
        Base URL: ``settings.binance_public_base_url`` (default ``https://api.binance.com``).
        """
        base = self._settings.binance_public_base_url.rstrip("/")
        result: dict[str, float] = {}
        timeout = httpx.Timeout(_REQUEST_TIMEOUT_SEC)

        with httpx.Client(timeout=timeout) as client:
            for raw in symbols:
                sym = raw.strip().upper()
                if not sym:
                    continue
                url = f"{base}{_PUBLIC_TICKER_PRICE_PATH}"
                try:
                    response = client.get(url, params={"symbol": sym})
                    response.raise_for_status()
                    data: Any = response.json()
                    price_raw = data.get("price")
                    if price_raw is None:
                        raise ValueError(f"Missing 'price' in response for {sym}")
                    result[sym] = float(price_raw)
                except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    logger.warning(
                        "Public ticker failed for %s: %s",
                        sym,
                        exc,
                    )
                    raise RuntimeError(f"Failed to fetch price for {sym}") from exc

        return result

    def get_public_24h_tickers(self, symbols: list[str]) -> dict[str, dict[str, float]]:
        """
        Fetch 24h public ticker stats for symbols from Binance public API.

        Endpoint: ``GET /api/v3/ticker/24hr?symbol=BTCUSDT``.
        Returned fields are normalized to floats and safe for the AI team.
        """
        base = self._settings.binance_public_base_url.rstrip("/")
        result: dict[str, dict[str, float]] = {}
        timeout = httpx.Timeout(_REQUEST_TIMEOUT_SEC)

        with httpx.Client(timeout=timeout) as client:
            for raw in symbols:
                sym = raw.strip().upper()
                if not sym:
                    continue
                url = f"{base}{_PUBLIC_TICKER_24HR_PATH}"
                try:
                    response = client.get(url, params={"symbol": sym})
                    response.raise_for_status()
                    data: Any = response.json()
                    result[sym] = {
                        "latest_price": float(data.get("lastPrice") or 0.0),
                        "open_price": float(data.get("openPrice") or 0.0),
                        "high_price": float(data.get("highPrice") or 0.0),
                        "low_price": float(data.get("lowPrice") or 0.0),
                        "price_change": float(data.get("priceChange") or 0.0),
                        "price_change_percent_24h": float(
                            data.get("priceChangePercent") or 0.0,
                        ),
                        "volume": float(data.get("volume") or 0.0),
                        "quote_volume": float(data.get("quoteVolume") or 0.0),
                    }
                except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    logger.warning("Public 24h ticker failed for %s: %s", sym, exc)
                    raise RuntimeError(f"Failed to fetch 24h ticker for {sym}") from exc

        return result

    def get_public_klines(
        self,
        symbol: str,
        *,
        interval: str = "15m",
        limit: int = 120,
    ) -> list[list[Any]]:
        """Fetch public Binance mainnet klines for read-only analysis."""
        sym = symbol.strip().upper()
        lim = max(20, min(int(limit), 1000))
        base = self._settings.binance_public_base_url.rstrip("/")
        url = f"{base}/api/v3/klines"
        with httpx.Client(timeout=self._timeout()) as client:
            response = client.get(
                url,
                params={"symbol": sym, "interval": interval.strip(), "limit": lim},
            )
            response.raise_for_status()
            data: Any = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected public klines shape for {sym}")
        return data
