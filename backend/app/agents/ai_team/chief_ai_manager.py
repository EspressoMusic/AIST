"""Chief AI Manager for the 4-agent trading team.

The manager is advisory-only. It combines agent outputs into one final decision
and never places orders or bypasses the existing execution gate.
"""

from __future__ import annotations

from typing import Any

from app.agents.ai_team.base_agent import AgentAction, AgentResponse, AiTeamContext, RiskLevel
from app.demo_bot_constants import TESTNET_DEV_SL_PCT, TESTNET_DEV_TP_PCT


class ChiefAiManager:
    """Combine the 4 AI team agents into one final advisory decision."""

    def decide(
        self,
        *,
        context: AiTeamContext,
        agent_outputs: list[AgentResponse],
    ) -> dict[str, Any]:
        agents = {item.agent_name: item for item in agent_outputs}
        risk = agents.get("Risk & Execution Agent")
        technical = agents.get("Technical / Quant Agent")
        macro = agents.get("Macro & Sentiment Agent")
        asset = agents.get("Asset Scout Agent")

        selected_symbol, asset_is_strong, asset_score = self._selected_asset(context, asset)
        execution_gate = self._execution_gate(
            risk=risk,
            technical=technical,
            asset=asset,
            macro=macro,
            asset_is_strong=asset_is_strong,
            selected_symbol=selected_symbol,
            context_symbol=context.symbol,
        )
        final_confidence = self._final_confidence(
            risk=risk,
            technical=technical,
            asset=asset,
            macro=macro,
            asset_is_strong=asset_is_strong,
        )

        can_buy = (
            execution_gate["risk_allows_trade"]
            and execution_gate["technical_allows_buy"]
            and execution_gate["asset_allows_buy"]
            and execution_gate["selected_symbol_matches_context"]
            and execution_gate["macro_allows_buy"]
            and final_confidence >= 75.0
        )
        final_action: AgentAction = "BUY" if can_buy else "HOLD"
        if final_action == "HOLD":
            final_confidence = min(final_confidence, 74.0)

        final_risk_level = self._final_risk_level(risk, technical, macro, final_action)
        position_size = float(getattr(risk, "position_size", 0.0) or 0.0) if can_buy else 0.0
        block_reasons = [
            str(row["reason"])
            for row in execution_gate["checks"].values()
            if row.get("passed") is False
        ]
        if can_buy:
            short_reason = "Chief AI approves advisory BUY"
            final_reason = (
                f"Risk allowed the trade, Technical is BUY, Asset Scout selected "
                f"{selected_symbol} with strength {asset_score:.2f}, and final confidence "
                f"is {final_confidence:.2f}. No order was executed."
            )
        else:
            short_reason = "Chief AI holds"
            final_reason = (
                "Final action is HOLD because "
                + (" ".join(block_reasons) if block_reasons else "confidence is below the BUY threshold.")
                + " No order was executed."
            )

        return {
            "selected_symbol": selected_symbol,
            "final_action": final_action,
            "final_confidence": round(final_confidence, 2),
            "final_risk_level": final_risk_level,
            "trade_allowed": bool(can_buy),
            "position_size": round(position_size, 2),
            "take_profit_pct": abs(float(TESTNET_DEV_TP_PCT)),
            "stop_loss_pct": abs(float(TESTNET_DEV_SL_PCT)),
            "final_reason": final_reason,
            "short_reason": short_reason,
            "agent_summary": self._agent_summary(agents),
            "execution_gate": execution_gate,
        }

    def _selected_asset(
        self,
        context: AiTeamContext,
        asset: AgentResponse | None,
    ) -> tuple[str, bool, float]:
        if asset is None:
            return context.symbol, False, 0.0
        data = asset.data_used or {}
        ranked = data.get("ranked_assets")
        best_symbol = str(data.get("best_symbol") or context.symbol).upper()
        best_score = 0.0
        if isinstance(ranked, list) and ranked:
            first = ranked[0]
            if isinstance(first, dict):
                best_symbol = str(first.get("symbol") or best_symbol).upper()
                best_score = float(first.get("strength_score") or 0.0)
        else:
            scores = data.get("strength_score_by_symbol")
            if isinstance(scores, dict):
                best_score = float(scores.get(best_symbol) or 0.0)
        return best_symbol, best_score >= 58.0, best_score

    def _execution_gate(
        self,
        *,
        risk: AgentResponse | None,
        technical: AgentResponse | None,
        asset: AgentResponse | None,
        macro: AgentResponse | None,
        asset_is_strong: bool,
        selected_symbol: str,
        context_symbol: str,
    ) -> dict[str, Any]:
        risk_allows = bool(risk and not risk.veto and risk.trade_allowed is True)
        technical_action = technical.action if technical else "HOLD"
        asset_action = asset.action if asset else "HOLD"
        macro_status = macro.current_status if macro else "MOCK"
        macro_data = macro.data_used if macro else {}
        macro_bias = str(
            (macro_data or {}).get("news_sentiment")
            or (macro_data or {}).get("market_bias")
            or "NEUTRAL",
        ).upper()
        macro_confidence = float(macro.confidence if macro else 0.0)
        news_items_count = int((macro_data or {}).get("news_items_count") or 0)
        macro_bearish_block = (
            macro_bias == "BEARISH"
            and macro_confidence >= 65.0
            and macro_status != "MOCK"
        )
        macro_no_news_block = (
            macro_status == "MOCK"
            and bool(macro)
            and context_symbol in {"AAPL", "TSLA", "NVDA", "SPY", "QQQ"}
        ) or (macro_status != "MOCK" and news_items_count <= 0 and context_symbol in {"AAPL", "TSLA", "NVDA", "SPY", "QQQ"})
        macro_blocks = bool(
            (macro and macro.veto and macro_status != "MOCK")
            or macro_bearish_block
            or macro_no_news_block
        )
        checks = {
            "risk_gate": {
                "passed": risk_allows,
                "reason": (
                    "Risk Agent allows trading."
                    if risk_allows
                    else "Risk Agent vetoed or did not allow trading."
                ),
                "veto": bool(risk.veto) if risk else True,
            },
            "technical_buy_signal": {
                "passed": technical_action == "BUY",
                "reason": (
                    "Technical Agent is BUY."
                    if technical_action == "BUY"
                    else f"Technical Agent is {technical_action}; Chief AI will not BUY."
                ),
            },
            "asset_strength": {
                "passed": asset_is_strong and asset_action == "BUY",
                "reason": (
                    f"Asset Scout selected strong asset {selected_symbol}."
                    if asset_is_strong and asset_action == "BUY"
                    else "Asset Scout did not approve a strong BUY candidate for the focused symbol."
                ),
            },
            "selected_symbol_matches_context": {
                "passed": selected_symbol == context_symbol,
                "reason": (
                    "Selected symbol matches the technical analysis symbol."
                    if selected_symbol == context_symbol
                    else f"Asset Scout prefers {selected_symbol}, but technical analysis is for {context_symbol}."
                ),
            },
            "macro_gate": {
                "passed": not macro_blocks,
                "reason": (
                    "Macro has no real stock news; Chief falls back to HOLD."
                    if macro_no_news_block
                    else "Macro is strongly bearish; Chief will not BUY."
                    if macro_bearish_block
                    else "Macro is MOCK/neutral and cannot block alone."
                    if macro_status == "MOCK"
                    else "Macro did not veto."
                    if not macro_blocks
                    else "Macro vetoed with real/AI data."
                ),
                "status": macro_status,
                "news_sentiment": macro_bias,
                "confidence": macro_confidence,
            },
        }
        return {
            "advisory_only": True,
            "can_execute_trades": False,
            "risk_allows_trade": risk_allows,
            "technical_allows_buy": technical_action == "BUY",
            "asset_allows_buy": asset_is_strong and asset_action == "BUY",
            "selected_symbol_matches_context": selected_symbol == context_symbol,
            "macro_blocks": macro_blocks,
            "macro_allows_buy": not macro_blocks,
            "confidence_threshold": 75.0,
            "checks": checks,
        }

    def _final_confidence(
        self,
        *,
        risk: AgentResponse | None,
        technical: AgentResponse | None,
        asset: AgentResponse | None,
        macro: AgentResponse | None,
        asset_is_strong: bool,
    ) -> float:
        risk_conf = float(risk.confidence if risk else 0.0)
        tech_conf = float(technical.confidence if technical else 0.0)
        asset_conf = float(asset.confidence if asset else 0.0)
        macro_conf = float(macro.confidence if macro else 0.0)
        confidence = risk_conf * 0.35 + tech_conf * 0.35 + asset_conf * 0.25
        if macro is not None and macro.current_status != "MOCK":
            macro_data = macro.data_used or {}
            analyst_bias = str(macro_data.get("analyst_bias") or "UNKNOWN").upper()
            news_items_count = int(macro_data.get("news_items_count") or 0)
            confidence += macro_conf * 0.05
            if macro.action == "SELL":
                confidence -= 12.0
            elif macro.action == "HOLD":
                confidence -= 4.0
            if analyst_bias == "UNKNOWN":
                confidence -= 4.0
            if news_items_count <= 0:
                confidence -= 8.0
        elif macro is not None and macro.action == "SELL":
            confidence -= 5.0
        if not asset_is_strong:
            confidence -= 10.0
        return max(0.0, min(100.0, confidence))

    def _final_risk_level(
        self,
        risk: AgentResponse | None,
        technical: AgentResponse | None,
        macro: AgentResponse | None,
        final_action: AgentAction,
    ) -> RiskLevel:
        levels = [
            item.risk_level
            for item in (risk, technical, macro)
            if item is not None
        ]
        if "HIGH" in levels or final_action == "HOLD" and risk and risk.veto:
            return "HIGH"
        if "MEDIUM" in levels:
            return "MEDIUM"
        return "LOW"

    def _agent_summary(self, agents: dict[str, AgentResponse]) -> dict[str, Any]:
        return {
            name: {
                "action": item.action,
                "confidence": item.confidence,
                "risk_level": item.risk_level,
                "veto": item.veto,
                "current_status": item.current_status,
                "short_reason": item.short_reason,
            }
            for name, item in agents.items()
        }
