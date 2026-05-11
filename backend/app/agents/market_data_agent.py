"""Market data collection — synthetic candles from seed (no external APIs)."""

from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime, timezone
from typing import Any

from app.models.agent_model import AgentResultModel


def _seed(symbol: str, tick_hint: float) -> int:
    raw = f"{symbol}|{tick_hint:.0f}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big")


def collect(
    symbol: str,
    mid: float,
    price_map: dict[str, float],
    *,
    tick_hint: float,
    bars: int = 64,
) -> AgentResultModel:
    """Build OHLCV + simple vol/trend reads (mock venue stream)."""
    rng = random.Random(_seed(symbol, tick_hint))
    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    volumes: list[float] = []
    o = mid * (1.0 + rng.uniform(-0.0005, 0.0005))
    last = o
    for i in range(bars):
        step = mid * rng.uniform(-0.0012, 0.0012) * (1.0 + 0.35 * math.sin(i / 5.0))
        c = max(last + step, mid * 0.5)
        wick = abs(rng.gauss(0, mid * 0.0008))
        hi = c + wick
        lo = c - wick * rng.uniform(0.6, 1.4)
        vol = abs(rng.gauss(1200.0, 200.0)) * (1.0 + abs(step) / (mid * 0.001 + 1e-9))
        highs.append(hi)
        lows.append(lo)
        closes.append(c)
        volumes.append(vol)
        last = c

    rets = [
        (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] > 0 else 0.0
        for i in range(1, len(closes))
    ]
    vol_realized = (
        math.sqrt(sum(r * r for r in rets[-20:]) / max(1, len(rets[-20:]))) if rets else 0.0
    )
    slope = (closes[-1] - closes[-10]) / closes[-10] if len(closes) >= 11 and closes[-10] > 0 else 0.0

    peer_prices = {k: float(v) for k, v in price_map.items() if k != symbol}
    cross_disp = 0.0
    if peer_prices:
        cross_disp = sum(abs(float(mid) - v) / mid for v in peer_prices.values()) / len(
            peer_prices,
        )

    payload: dict[str, Any] = {
        "provider": "mock_synthetic",
        "symbol": symbol.strip().upper(),
        "last_price": closes[-1],
        "reference_mid": mid,
        "bar_count": len(closes),
        "closes": [round(x, 8) for x in closes],
        "highs": [round(x, 8) for x in highs],
        "lows": [round(x, 8) for x in lows],
        "volumes": [round(x, 4) for x in volumes],
        "recent_close_sample": [round(x, 6) for x in closes[-5:]],
        "volume_last": round(volumes[-1], 2),
        "volume_mean_20": round(sum(volumes[-20:]) / min(20, len(volumes)), 2),
        "realized_vol_short": round(vol_realized, 6),
        "trend_slope_10": round(slope, 6),
        "cross_symbol_dispersion": round(cross_disp, 6),
        "notes": "Synthetic walk from hash seed — replace with venue WebSocket + REST later.",
    }

    score = max(
        -40.0,
        min(40.0, slope * 9000.0 + (vol_realized - 0.001) * 8000.0),
    )

    return AgentResultModel(
        agent_name="Market Data Agent",
        symbol=symbol,
        status="completed",
        score=round(score, 2),
        action=None,
        confidence=88.0,
        explanation=(
            f"Mock stream: {len(closes)} bars, short vol={vol_realized:.4f}, "
            f"10-bar slope={slope:.5f}."
        ),
        created_at=datetime.now(timezone.utc),
        payload=payload,
    )
