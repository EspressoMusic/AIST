"""Asset Scout Agent."""

from __future__ import annotations

from app.agents.ai_team.base_agent import AgentResponse, AiTeamContext, BaseAiTeamAgent


class AssetScoutAgent(BaseAiTeamAgent):
    agent_name = "Asset Scout Agent"
    role = "Find the best asset opportunities from the watched symbols."

    def analyze(self, context: AiTeamContext) -> AgentResponse:
        scored_assets = self._score_assets(context)
        best_symbol = scored_assets[0]["symbol"] if scored_assets else context.symbol
        weakest_symbol = scored_assets[-1]["symbol"] if scored_assets else context.symbol
        focus_is_best = context.symbol == best_symbol
        best_score = float(scored_assets[0]["strength_score"]) if scored_assets else 0.0
        weakest_score = float(scored_assets[-1]["strength_score"]) if scored_assets else 0.0
        score_gap = best_score - weakest_score

        if focus_is_best and best_score >= 58:
            action = "BUY"
            confidence = min(88.0, 54.0 + best_score * 0.45)
            risk_level = "MEDIUM"
            short_reason = f"{context.symbol} ranks strongest"
        elif not focus_is_best:
            action = "HOLD"
            confidence = min(82.0, 55.0 + max(0.0, score_gap) * 0.28)
            risk_level = "MEDIUM"
            short_reason = f"Watch {best_symbol} before {context.symbol}"
        else:
            action = "HOLD"
            confidence = 52.0
            risk_level = "LOW"
            short_reason = "No standout asset yet"

        status_label = context.asset_current_status
        reason = (
            f"Asset Scout ranked {len(scored_assets)} watched symbols using "
            f"{status_label}. Best={best_symbol}, weakest={weakest_symbol}. "
            "Strength combines 24h change, recent movement, quote volume, and "
            "intraday range when available."
        )

        return self.response(
            action=action,  # type: ignore[arg-type]
            confidence=confidence,
            risk_level=risk_level,  # type: ignore[arg-type]
            veto=False,
            short_reason=short_reason,
            reason=reason,
            data_used={
                "watched_symbols": context.watched_symbols,
                "ranked_assets": scored_assets,
                "best_symbol": best_symbol,
                "weakest_symbol": weakest_symbol,
                "strength_score_by_symbol": {
                    row["symbol"]: row["strength_score"] for row in scored_assets
                },
                "reason": reason,
                "data_sources": context.asset_data_sources,
                "current_status": context.asset_current_status,
                "fallback_reason": context.asset_fallback_reason,
                "correlation": "placeholder",
                "hot_or_ignored_assets": "placeholder",
                "focus_symbol": context.symbol,
            },
        )

    def _score_assets(self, context: AiTeamContext) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        market = context.asset_market_data or {}
        quote_volumes = [
            float((market.get(symbol) or {}).get("quote_volume") or 0.0)
            for symbol in context.watched_symbols
        ]
        max_quote_volume = max(quote_volumes) if quote_volumes else 0.0

        for symbol in context.watched_symbols:
            row = dict(market.get(symbol) or {})
            latest = float(row.get("latest_price") or context.prices.get(symbol) or 0.0)
            change_24h = float(row.get("price_change_percent_24h") or 0.0)
            movement = float(row.get("recent_price_movement_pct") or change_24h)
            quote_volume = float(row.get("quote_volume") or 0.0)
            high = float(row.get("high_price") or 0.0)
            low = float(row.get("low_price") or 0.0)
            range_pct = ((high - low) / latest * 100.0) if latest > 0 and high > low else 0.0
            volume_component = (
                quote_volume / max_quote_volume * 25.0 if max_quote_volume > 0 else 0.0
            )
            momentum_component = max(-25.0, min(35.0, change_24h * 4.0))
            movement_component = max(-15.0, min(20.0, movement * 2.0))
            range_component = max(0.0, min(10.0, range_pct))
            strength_score = max(
                0.0,
                min(
                    100.0,
                    45.0
                    + momentum_component
                    + movement_component
                    + volume_component
                    + range_component,
                ),
            )
            rows.append(
                {
                    "symbol": symbol,
                    "latest_price": round(latest, 8),
                    "recent_price_movement_pct": round(movement, 4),
                    "change_24h_pct": round(change_24h, 4),
                    "volume": round(float(row.get("volume") or 0.0), 4),
                    "quote_volume": round(quote_volume, 4),
                    "intraday_range_pct": round(range_pct, 4),
                    "strength_score": round(strength_score, 2),
                    "source": row.get("source"),
                    "price_source": row.get("price_source"),
                    "fallback_reason": row.get("fallback_reason"),
                },
            )

        return sorted(rows, key=lambda item: float(item["strength_score"]), reverse=True)
