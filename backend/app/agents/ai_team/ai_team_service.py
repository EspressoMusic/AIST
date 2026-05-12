"""Service that runs the 4-agent AI trading team preview."""

from __future__ import annotations

from typing import Any

from app.agents.ai_team.asset_scout_agent import AssetScoutAgent
from app.agents.ai_team.base_agent import AgentResponse, AiTeamContext
from app.agents.ai_team.chief_ai_manager import ChiefAiManager
from app.agents.ai_team.macro_sentiment_agent import MacroSentimentAgent
from app.agents.ai_team.risk_execution_agent import RiskExecutionAgent
from app.agents.ai_team.technical_quant_agent import TechnicalQuantAgent
from app.services.bot_state_service import BotStateService
from app.services.exchange_service import ExchangeService
from app.services.alpaca_paper_service import AlpacaPaperService
from app.services.alpaca_news_service import AlpacaNewsService
from app.services.analyst_data_service import AnalystDataService
from app.services.ai_provider_service import AIProviderService
from app.services.news_data_service import NewsDataService
from app.config import Settings
from app.demo_bot_constants import (
    ALPACA_AI_TEAM_WATCHED_SYMBOLS,
    ALPACA_PAPER_DEFAULT_ORDER_USD,
    DEMO_MAX_ORDER_USDT,
    EXEC_GATE_DAILY_MAX_LOSS_USDT,
    EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS,
    EXEC_GATE_MAX_OPENS_PER_DAY,
    TESTNET_MARKET_BUY_QUOTE_USDT,
    TESTNET_STRATEGY_MAX_CONSECUTIVE_LOSSES,
)
from app.models.decision_model import DecisionModel
from app.models.demo_trade import closed_trade_realized_pl
from app.models.execution_mode import ExecutionMode

_WATCHED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
_ALPACA_WATCHED_SYMBOLS = list(ALPACA_AI_TEAM_WATCHED_SYMBOLS)
_AGENT_KEYS = {
    "Risk & Execution Agent": "RISK",
    "Macro & Sentiment Agent": "MACRO",
    "Technical / Quant Agent": "TECHNICAL",
    "Asset Scout Agent": "ASSET_SCOUT",
}


class AiTeamService:
    def __init__(
        self,
        *,
        exchange: ExchangeService,
        state: BotStateService,
        settings: Settings,
        news_data: NewsDataService | None = None,
        ai_provider: AIProviderService | None = None,
        alpaca_paper: AlpacaPaperService | None = None,
        alpaca_news: AlpacaNewsService | None = None,
        analyst_data: AnalystDataService | None = None,
    ) -> None:
        self._exchange = exchange
        self._state = state
        self._settings = settings
        self._ai_provider = ai_provider
        self._alpaca = alpaca_paper
        self._execution_bridge: Any | None = None
        self._agents = [
            RiskExecutionAgent(),
            MacroSentimentAgent(
                news_data=news_data,
                ai_provider=ai_provider,
                alpaca_news=alpaca_news,
                analyst_data=analyst_data,
            ),
            TechnicalQuantAgent(),
            AssetScoutAgent(),
        ]
        self._chief = ChiefAiManager()

    def set_execution_bridge(self, bridge: Any | None) -> None:
        self._execution_bridge = bridge

    def preview(self, symbol: str = "BTCUSDT", *, debug: bool = False) -> dict[str, Any]:
        context = self._build_context(symbol)
        outputs: list[AgentResponse] = [agent.analyze(context) for agent in self._agents]
        chief_decision = self._chief.decide(context=context, agent_outputs=outputs)
        self._state.set_last_chief_decision(chief_decision)
        decision_log = self._decision_log_from_preview(
            context=context,
            outputs=outputs,
            chief_decision=chief_decision,
        )
        bridge_result = self._run_safe_execution_bridge(decision_log, chief_decision)
        decision_log = self._decision_with_bridge_result(decision_log, bridge_result)
        self._state.append_decision(decision_log)
        system_status = {
            "current_status": "REAL_DATA",
            "advisory_only": True,
            "can_execute_trades": False,
            "agent_count": len(outputs),
            "chief_manager": "ACTIVE",
            "execution_mode": context.execution_mode,
            "message": "AI team preview is advisory only and does not change current bot trading logic.",
        }
        response = {
            "symbol": context.symbol,
            "system_status": system_status,
            "mode": "MOCK_INTERNAL_ONLY",
            "can_execute_trades": False,
            "message": "AI team preview is advisory only and does not change current bot trading logic.",
            "context": self._context_summary(context),
            "indicators_summary": self._indicators_summary(outputs),
            "ranked_assets_summary": self._ranked_assets_summary(outputs),
            "news_items": self._news_items_summary(outputs),
            "macro_sentiment_summary": self._macro_sentiment_summary(outputs),
            "analyst_summary": self._analyst_summary(outputs),
            "agents": [output.model_dump() for output in outputs],
            "chief_decision": chief_decision,
            "execution_bridge": bridge_result,
        }
        if debug:
            response["debug"] = {
                "context": context.model_dump(),
                "note": "Full raw AI team context, including candles and market snapshots.",
            }
        return response

    def status(self) -> dict[str, Any]:
        context = self._build_context(self._default_symbol_for_mode())
        outputs: list[AgentResponse] = [agent.analyze(context) for agent in self._agents]
        return {
            "agents_total": len(outputs),
            "agents": [
                {
                    "name": output.agent_name,
                    "status": output.current_status,
                    "data_sources": list(output.data_used.get("data_sources") or []),
                    "can_execute_trades": False,
                }
                for output in outputs
            ],
            "chief_manager_ready": True,
            "execution_enabled": False,
            "ai_provider": self._ai_provider_status(),
            "execution_mode": context.execution_mode,
        }

    def chat(
        self,
        *,
        message: str,
        target_agent: str = "ALL",
        symbol: str = "BTCUSDT",
    ) -> dict[str, Any]:
        """Advisory-only AI team chat. It never logs decisions or executes trades."""
        clean = message.strip()
        target = target_agent.strip().upper() or "ALL"
        context = self._build_context(symbol)
        outputs: list[AgentResponse] = [agent.analyze(context) for agent in self._agents]
        chief_decision = self._chief.decide(context=context, agent_outputs=outputs)
        selected_keys = self._chat_targets(clean, target)
        messages = [
            self._chat_message_from_agent(output, clean)
            for output in outputs
            if _AGENT_KEYS.get(output.agent_name) in selected_keys
        ]
        messages = [item for item in messages if item is not None]
        chief_summary = None
        if target in {"ALL", "CHIEF"} or "CHIEF" in selected_keys:
            chief_summary = {
                "text": self._chief_chat_text(chief_decision, clean),
                "action": chief_decision.get("final_action", "HOLD"),
                "confidence": chief_decision.get("final_confidence", 0.0),
            }
            if target == "CHIEF":
                messages = [
                    {
                        "sender": "Chief AI Manager",
                        "agent_key": "CHIEF",
                        "text": chief_summary["text"],
                        "short_text": str(chief_decision.get("short_reason") or "Chief summary"),
                        "confidence": chief_summary["confidence"],
                        "risk_level": chief_decision.get("final_risk_level", "MEDIUM"),
                        "action": chief_summary["action"],
                    },
                ]
        return {
            "messages": messages,
            "chief_summary": chief_summary,
            "advisory_only": True,
            "can_execute_trades": False,
        }

    def _build_context(self, symbol: str) -> AiTeamContext:
        if self._state.execution_mode == ExecutionMode.ALPACA_PAPER:
            return self._build_alpaca_context(symbol)
        return self._build_crypto_context(symbol)

    def _build_crypto_context(self, symbol: str) -> AiTeamContext:
        requested = symbol.strip().upper() or "BTCUSDT"
        market_snapshot = self._exchange.get_asset_market_snapshot(_WATCHED_SYMBOLS)
        asset_market_data = {
            key: dict(value)
            for key, value in dict(market_snapshot.get("assets") or {}).items()
            if isinstance(value, dict)
        }
        prices = {
            key: float(value.get("latest_price") or 0.0)
            for key, value in asset_market_data.items()
        }
        data_sources = [
            str(item) for item in list(market_snapshot.get("data_sources") or [])
        ]
        data_source = ",".join(data_sources) if data_sources else "unknown"
        if requested not in prices:
            requested = "BTCUSDT" if "BTCUSDT" in prices else next(iter(prices), "BTCUSDT")
        technical_snapshot = self._exchange.get_technical_klines_snapshot(requested)
        technical_sources = [
            str(item) for item in list(technical_snapshot.get("data_sources") or [])
        ]

        exec_snapshot = self._state.exec_gate_snapshot()
        risk_snapshot = self._build_risk_snapshot(requested, exec_snapshot)
        return AiTeamContext(
            symbol=requested,
            watched_symbols=_WATCHED_SYMBOLS,
            prices=prices,
            current_price=float(prices.get(requested, 0.0)),
            open_positions=self._state.effective_open_positions_for_risk(),
            daily_loss=float(exec_snapshot.get("realized_pnl_today") or 0.0),
            trade_count_today=int(exec_snapshot.get("opens_today") or 0),
            consecutive_losses=self._state.consecutive_closed_losses(requested),
            decisions_count=len(self._state.decisions_newest_first()),
            execution_mode=self._state.execution_mode.value,
            data_source=data_source,
            asset_market_data=asset_market_data,
            asset_data_sources=data_sources,
            asset_current_status=str(
                market_snapshot.get("current_status") or "MOCK",
            ),  # type: ignore[arg-type]
            technical_candles=[
                dict(item)
                for item in list(technical_snapshot.get("candles") or [])
                if isinstance(item, dict)
            ],
            technical_data_sources=technical_sources,
            technical_current_status=str(
                technical_snapshot.get("current_status") or "MOCK",
            ),  # type: ignore[arg-type]
            risk_snapshot=risk_snapshot,
        )

    def _build_alpaca_context(self, symbol: str) -> AiTeamContext:
        requested = symbol.strip().upper() or "AAPL"
        if requested not in _ALPACA_WATCHED_SYMBOLS:
            requested = "AAPL"
        if self._alpaca is None:
            market_snapshot = {
                "current_status": "MOCK",
                "data_sources": ["mock_alpaca_unconfigured"],
                "assets": {},
                "error": "Alpaca Paper service is not configured.",
            }
        else:
            market_snapshot = self._alpaca.get_stock_market_snapshot(_ALPACA_WATCHED_SYMBOLS)
        asset_market_data = {
            key: dict(value)
            for key, value in dict(market_snapshot.get("assets") or {}).items()
            if isinstance(value, dict)
        }
        prices = {
            key: float(value.get("latest_price") or 0.0)
            for key, value in asset_market_data.items()
        }
        selected = requested
        technical_snapshot = (
            self._alpaca.get_stock_bars_snapshot(selected)
            if self._alpaca is not None
            else {
                "current_status": "MOCK",
                "data_sources": ["mock_alpaca_unconfigured"],
                "candles": [],
            }
        )
        technical_sources = [
            str(item) for item in list(technical_snapshot.get("data_sources") or [])
        ]
        data_sources = [
            str(item) for item in list(market_snapshot.get("data_sources") or [])
        ]
        risk_snapshot = self._build_alpaca_risk_snapshot(selected)
        return AiTeamContext(
            symbol=selected,
            watched_symbols=_ALPACA_WATCHED_SYMBOLS,
            prices=prices,
            current_price=float(prices.get(selected, 0.0)),
            open_positions=int(risk_snapshot.get("current_open_position_count") or 0),
            daily_loss=float(risk_snapshot.get("daily_loss") or 0.0),
            trade_count_today=int(risk_snapshot.get("trade_count_today") or 0),
            consecutive_losses=self._state.consecutive_closed_losses(selected),
            decisions_count=len(self._state.decisions_newest_first()),
            execution_mode=self._state.execution_mode.value,
            data_source=",".join(data_sources) if data_sources else "alpaca_paper",
            asset_market_data=asset_market_data,
            asset_data_sources=data_sources,
            asset_current_status=str(
                market_snapshot.get("current_status") or "MOCK",
            ),  # type: ignore[arg-type]
            technical_candles=[
                dict(item)
                for item in list(technical_snapshot.get("candles") or [])
                if isinstance(item, dict)
            ],
            technical_data_sources=technical_sources,
            technical_current_status=str(
                technical_snapshot.get("current_status") or "MOCK",
            ),  # type: ignore[arg-type]
            risk_snapshot=risk_snapshot,
        )

    def _default_symbol_for_mode(self) -> str:
        if self._state.execution_mode == ExecutionMode.ALPACA_PAPER:
            return "AAPL"
        return "BTCUSDT"

    def _strongest_symbol_from_market(
        self,
        market: dict[str, dict[str, Any]],
        *,
        fallback: str,
        watched: list[str],
    ) -> str:
        best_symbol = fallback
        best_score = -1.0
        max_quote_volume = max(
            [
                float((market.get(symbol) or {}).get("quote_volume") or 0.0)
                for symbol in watched
            ]
            or [0.0],
        )
        for symbol in watched:
            row = dict(market.get(symbol) or {})
            latest = float(row.get("latest_price") or 0.0)
            change_24h = float(row.get("price_change_percent_24h") or 0.0)
            movement = float(row.get("recent_price_movement_pct") or change_24h)
            quote_volume = float(row.get("quote_volume") or 0.0)
            high = float(row.get("high_price") or 0.0)
            low = float(row.get("low_price") or 0.0)
            range_pct = ((high - low) / latest * 100.0) if latest > 0 and high > low else 0.0
            volume_component = (
                quote_volume / max_quote_volume * 25.0 if max_quote_volume > 0 else 0.0
            )
            score = (
                45.0
                + max(-25.0, min(35.0, change_24h * 4.0))
                + max(-15.0, min(20.0, movement * 2.0))
                + max(0.0, min(10.0, range_pct))
                + volume_component
            )
            if score > best_score:
                best_score = score
                best_symbol = symbol
        return best_symbol

    def _build_alpaca_risk_snapshot(self, symbol: str) -> dict[str, Any]:
        exec_snapshot = self._state.exec_gate_snapshot()
        base = {
            "symbol": symbol,
            "execution_mode": self._state.execution_mode.value,
            "kill_switch_active": bool(self._settings.bot_kill_switch),
            "closed_trades_count": len([t for t in self._state.history_trades() if not t.is_open]),
            "daily_loss": float(exec_snapshot.get("realized_pnl_today") or 0.0),
            "daily_loss_limit": EXEC_GATE_DAILY_MAX_LOSS_USDT,
            "trade_count_today": int(exec_snapshot.get("opens_today") or 0),
            "daily_trade_limit": EXEC_GATE_MAX_OPENS_PER_DAY,
            "consecutive_losses": self._state.consecutive_closed_losses(symbol),
            "max_consecutive_losses": TESTNET_STRATEGY_MAX_CONSECUTIVE_LOSSES,
            "cooldown_active": False,
            "cooldown_reason": None,
            "global_open_cooldown_seconds": EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS,
            "last_open_utc": exec_snapshot.get("last_open_utc"),
            "drawdown_proxy": self._state.drawdown_proxy(),
            "exec_gate_snapshot": dict(exec_snapshot),
            "max_position_size": float(DEMO_MAX_ORDER_USDT),
            "suggested_position_size_default": float(ALPACA_PAPER_DEFAULT_ORDER_USD),
        }
        if self._alpaca is None:
            return {
                **base,
                "current_status": "MOCK",
                "data_available": False,
                "current_open_position_count": self._state.effective_open_positions_for_risk(),
                "open_trades_count": self._state.effective_open_positions_for_risk(),
                "open_trades": [],
                "portfolio": {},
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "buying_power": 0.0,
                "risk_error": "Alpaca Paper service is not configured.",
            }
        try:
            account = self._alpaca.get_account()
            positions = self._alpaca.get_positions()
            active_positions = [
                row for row in positions if abs(float(row.get("qty") or 0.0)) > 0.0
            ]
            buying_power = float(account.get("buying_power") or account.get("cash") or 0.0)
            equity = float(account.get("equity") or 0.0)
            last_equity = float(account.get("last_equity") or equity or 0.0)
            alpaca_daily_pnl = equity - last_equity
            daily_loss = min(float(base["daily_loss"]), alpaca_daily_pnl)
            max_position = max(
                0.0,
                min(float(DEMO_MAX_ORDER_USDT), float(ALPACA_PAPER_DEFAULT_ORDER_USD), buying_power * 0.1),
            )
            return {
                **base,
                "current_status": "REAL_DATA",
                "data_available": True,
                "alpaca_account": {
                    "status": account.get("status"),
                    "currency": account.get("currency"),
                    "cash": account.get("cash"),
                    "buying_power": account.get("buying_power"),
                    "equity": account.get("equity"),
                    "last_equity": account.get("last_equity"),
                },
                "buying_power": round(buying_power, 2),
                "cash": float(account.get("cash") or 0.0),
                "equity": equity,
                "daily_loss": round(daily_loss, 8),
                "alpaca_daily_pnl": round(alpaca_daily_pnl, 8),
                "open_trades": active_positions,
                "open_trades_count": len(active_positions),
                "current_open_position_count": len(active_positions),
                "portfolio": {
                    "equity": equity,
                    "cash": float(account.get("cash") or 0.0),
                    "buying_power": buying_power,
                    "alpaca_daily_pnl": alpaca_daily_pnl,
                },
                "realized_pnl": float(base["daily_loss"]),
                "unrealized_pnl": sum(float(row.get("unrealized_pl") or 0.0) for row in active_positions),
                "max_position_size": round(max_position, 2),
                "suggested_position_size_default": round(max_position, 2),
            }
        except Exception as exc:
            self._state.set_last_error(str(exc))
            return {
                **base,
                "current_status": "MOCK",
                "data_available": False,
                "current_open_position_count": self._state.effective_open_positions_for_risk(),
                "open_trades_count": self._state.effective_open_positions_for_risk(),
                "open_trades": [],
                "portfolio": {},
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "buying_power": 0.0,
                "risk_error": str(exc),
            }

    def _chat_targets(self, message: str, target: str) -> set[str]:
        if target in {"RISK", "MACRO", "TECHNICAL", "ASSET_SCOUT", "CHIEF"}:
            return {target}
        text = message.lower()
        selected: set[str] = set()
        if any(word in text for word in ("risk", "safe", "safety", "loss", "cooldown", "veto", "open trade")):
            selected.add("RISK")
        if any(word in text for word in ("news", "macro", "sentiment", "headline", "market mood")):
            selected.add("MACRO")
        if any(word in text for word in ("chart", "technical", "entry", "rsi", "ema", "indicator", "trend")):
            selected.add("TECHNICAL")
        if any(word in text for word in ("asset", "strongest", "watch", "symbol", "coin", "rank")):
            selected.add("ASSET_SCOUT")
        if any(word in text for word in ("chief", "summary", "final", "decision", "should we buy")):
            selected.add("CHIEF")
        return selected or {"RISK", "MACRO", "TECHNICAL", "ASSET_SCOUT", "CHIEF"}

    def _chat_message_from_agent(
        self,
        output: AgentResponse,
        user_message: str,
    ) -> dict[str, Any] | None:
        key = _AGENT_KEYS.get(output.agent_name)
        if key is None:
            return None
        detail = self._agent_detail_sentence(output, user_message)
        return {
            "sender": output.agent_name,
            "agent_key": key,
            "text": detail,
            "short_text": output.short_reason,
            "confidence": output.confidence,
            "risk_level": output.risk_level,
            "action": output.action,
        }

    def _agent_detail_sentence(self, output: AgentResponse, user_message: str) -> str:
        data = output.data_used or {}
        key = _AGENT_KEYS.get(output.agent_name)
        if key == "RISK":
            allowed = data.get("trade_allowed")
            checks = data.get("risk_checks")
            blocked = []
            if isinstance(checks, dict):
                blocked = [
                    str(row.get("reason") or name)
                    for name, row in checks.items()
                    if isinstance(row, dict) and row.get("veto") is True
                ]
            if blocked:
                return f"Risk check is blocking new trades: {' '.join(blocked)}"
            return (
                f"Risk is currently {'allowing' if allowed else 'not approving'} a trade. "
                f"{output.reason}"
            )
        if key == "MACRO":
            bias = data.get("news_sentiment") or data.get("market_bias") or "NEUTRAL"
            analyst_bias = data.get("analyst_bias") or "UNKNOWN"
            count = data.get("news_items_count", 0)
            return (
                f"Macro/news view is {bias} with analyst bias {analyst_bias} "
                f"from {count} news item(s). {output.reason}"
            )
        if key == "TECHNICAL":
            indicators = data.get("indicators") if isinstance(data.get("indicators"), dict) else data
            trend = indicators.get("trend_direction", "unclear") if isinstance(indicators, dict) else "unclear"
            rsi = indicators.get("rsi", "unknown") if isinstance(indicators, dict) else "unknown"
            return f"Technical view: trend is {trend}, RSI is {rsi}. {output.reason}"
        if key == "ASSET_SCOUT":
            best = data.get("best_symbol", "unknown")
            ranked = data.get("ranked_assets")
            score = None
            if isinstance(ranked, list) and ranked and isinstance(ranked[0], dict):
                score = ranked[0].get("strength_score")
            return f"Asset Scout is watching {best} as the strongest candidate (score {score}). {output.reason}"
        return output.reason

    def _chief_chat_text(self, chief_decision: dict[str, Any], user_message: str) -> str:
        action = chief_decision.get("final_action", "HOLD")
        confidence = chief_decision.get("final_confidence", 0.0)
        reason = chief_decision.get("final_reason") or chief_decision.get("short_reason") or ""
        return (
            f"Chief AI final advisory decision is {action} with {confidence}% confidence. "
            f"{reason} This chat is advisory only and never executes trades."
        )

    def _build_risk_snapshot(
        self,
        symbol: str,
        exec_snapshot: dict[str, object],
    ) -> dict[str, Any]:
        open_trades = list(self._state.snapshot_open_trades().values())
        history = self._state.history_trades()
        unrealized_pnl = sum(float(t.profit_loss or 0.0) for t in open_trades)
        realized_pnl = sum(closed_trade_realized_pl(t) for t in history if not t.is_open)
        cooldown_reason = self._state.testnet_buy_blocked_reason(symbol)
        last_open_utc = exec_snapshot.get("last_open_utc")
        return {
            "current_status": "REAL_DATA",
            "data_available": True,
            "symbol": symbol,
            "execution_mode": self._state.execution_mode.value,
            "kill_switch_active": bool(self._settings.bot_kill_switch),
            "open_trades_count": len(open_trades),
            "current_open_position_count": self._state.effective_open_positions_for_risk(),
            "open_trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "side": t.side,
                    "source": t.source,
                    "entry_price": t.entry_price,
                    "current_price": t.current_price,
                    "profit_loss": t.profit_loss,
                    "opened_at": t.opened_at.isoformat(),
                }
                for t in open_trades
            ],
            "closed_trades_count": len([t for t in history if not t.is_open]),
            "realized_pnl": round(realized_pnl, 8),
            "unrealized_pnl": round(unrealized_pnl, 8),
            "portfolio": {
                "realized_pnl": round(realized_pnl, 8),
                "unrealized_pnl": round(unrealized_pnl, 8),
                "total_pnl": round(realized_pnl + unrealized_pnl, 8),
            },
            "daily_loss": float(exec_snapshot.get("realized_pnl_today") or 0.0),
            "daily_loss_limit": EXEC_GATE_DAILY_MAX_LOSS_USDT,
            "trade_count_today": int(exec_snapshot.get("opens_today") or 0),
            "daily_trade_limit": EXEC_GATE_MAX_OPENS_PER_DAY,
            "consecutive_losses": self._state.consecutive_closed_losses(symbol),
            "max_consecutive_losses": TESTNET_STRATEGY_MAX_CONSECUTIVE_LOSSES,
            "cooldown_active": cooldown_reason is not None,
            "cooldown_reason": cooldown_reason,
            "global_open_cooldown_seconds": EXEC_GATE_GLOBAL_OPEN_COOLDOWN_SECONDS,
            "last_open_utc": last_open_utc,
            "suggested_position_size_default": TESTNET_MARKET_BUY_QUOTE_USDT,
            "drawdown_proxy": self._state.drawdown_proxy(),
            "exec_gate_snapshot": dict(exec_snapshot),
        }

    def _context_summary(self, context: AiTeamContext) -> dict[str, Any]:
        return {
            "symbol": context.symbol,
            "watched_symbols": context.watched_symbols,
            "current_price": context.current_price,
            "prices": context.prices,
            "execution_mode": context.execution_mode,
            "data_source": context.data_source,
            "open_positions": context.open_positions,
            "daily_loss": context.daily_loss,
            "trade_count_today": context.trade_count_today,
            "consecutive_losses": context.consecutive_losses,
            "decisions_count": context.decisions_count,
            "asset_current_status": context.asset_current_status,
            "asset_data_sources": context.asset_data_sources,
            "asset_count": len(context.asset_market_data),
            "technical_current_status": context.technical_current_status,
            "technical_data_sources": context.technical_data_sources,
            "technical_candle_count": len(context.technical_candles),
            "risk_status": context.risk_snapshot.get("current_status", "REAL_DATA"),
            "risk_snapshot_summary": {
                "kill_switch_active": context.risk_snapshot.get("kill_switch_active"),
                "current_open_position_count": context.risk_snapshot.get(
                    "current_open_position_count",
                ),
                "daily_loss": context.risk_snapshot.get("daily_loss"),
                "trade_count_today": context.risk_snapshot.get("trade_count_today"),
                "consecutive_losses": context.risk_snapshot.get("consecutive_losses"),
                "cooldown_active": context.risk_snapshot.get("cooldown_active"),
            },
        }

    def _indicators_summary(self, outputs: list[AgentResponse]) -> dict[str, Any]:
        technical = next(
            (item for item in outputs if item.agent_name == "Technical / Quant Agent"),
            None,
        )
        if technical is None:
            return {}
        data = technical.data_used or {}
        indicators = data.get("indicators")
        return dict(indicators) if isinstance(indicators, dict) else {
            key: data.get(key)
            for key in (
                "ema_fast",
                "ema_slow",
                "rsi",
                "volatility",
                "trend_direction",
                "entry_quality_score",
            )
            if key in data
        }

    def _ranked_assets_summary(self, outputs: list[AgentResponse]) -> list[dict[str, Any]]:
        asset = next(
            (item for item in outputs if item.agent_name == "Asset Scout Agent"),
            None,
        )
        if asset is None:
            return []
        ranked = asset.data_used.get("ranked_assets") if asset.data_used else []
        if not isinstance(ranked, list):
            return []
        return [
            dict(item)
            for item in ranked
            if isinstance(item, dict)
        ]

    def _macro_output(self, outputs: list[AgentResponse]) -> AgentResponse | None:
        return next(
            (item for item in outputs if item.agent_name == "Macro & Sentiment Agent"),
            None,
        )

    def _news_items_summary(self, outputs: list[AgentResponse]) -> list[dict[str, Any]]:
        macro = self._macro_output(outputs)
        if macro is None:
            return []
        data = macro.data_used or {}
        top_news = data.get("top_news")
        if isinstance(top_news, list):
            return [dict(item) for item in top_news if isinstance(item, dict)]
        news = data.get("news_items")
        if isinstance(news, list):
            return [dict(item) for item in news[:5] if isinstance(item, dict)]
        return []

    def _macro_sentiment_summary(self, outputs: list[AgentResponse]) -> dict[str, Any]:
        macro = self._macro_output(outputs)
        if macro is None:
            return {}
        data = macro.data_used or {}
        return {
            "status": macro.current_status,
            "action": macro.action,
            "confidence": macro.confidence,
            "risk_level": macro.risk_level,
            "sentiment_score": data.get("sentiment_score"),
            "news_sentiment": data.get("news_sentiment") or data.get("market_bias"),
            "analyst_bias": data.get("analyst_bias"),
            "news_items_count": data.get("news_items_count", 0),
            "data_sources": list(data.get("data_sources") or []),
            "short_reason": macro.short_reason,
            "reason": macro.reason,
        }

    def _analyst_summary(self, outputs: list[AgentResponse]) -> dict[str, Any]:
        macro = self._macro_output(outputs)
        if macro is None:
            return {}
        analyst = macro.data_used.get("analyst_summary") if macro.data_used else {}
        return dict(analyst) if isinstance(analyst, dict) else {}

    def _decision_log_from_preview(
        self,
        *,
        context: AiTeamContext,
        outputs: list[AgentResponse],
        chief_decision: dict[str, Any],
    ) -> DecisionModel:
        by_name = {output.agent_name: output for output in outputs}
        macro = by_name.get("Macro & Sentiment Agent")
        technical = by_name.get("Technical / Quant Agent")
        risk = by_name.get("Risk & Execution Agent")
        final_action = str(chief_decision.get("final_action") or "HOLD")
        final_confidence = float(chief_decision.get("final_confidence") or 0.0)
        final_reason = str(chief_decision.get("final_reason") or "")
        return DecisionModel(
            symbol=str(chief_decision.get("selected_symbol") or context.symbol),
            final_action=final_action,
            confidence=final_confidence,
            news_score=float(macro.confidence if macro else 0.0),
            technical_score=float(technical.confidence if technical else 0.0),
            risk_score=float(risk.confidence if risk else 0.0),
            risk_approved=bool(chief_decision.get("trade_allowed")),
            explanation=f"Chief AI Team preview: {final_reason}",
            brain={
                "source": "CHIEF_AI_TEAM_PREVIEW",
                "selected_symbol": chief_decision.get("selected_symbol"),
                "final_action": final_action,
                "final_confidence": final_confidence,
                "final_reason": final_reason,
                "trade_allowed": chief_decision.get("trade_allowed"),
                "agents": [output.model_dump() for output in outputs],
                "chief_decision": chief_decision,
                "execution_gate": chief_decision.get("execution_gate"),
            },
            final_confidence=final_confidence,
            final_reasons=[final_reason],
        )

    def _ai_provider_status(self) -> str:
        if self._ai_provider is not None:
            status = self._ai_provider.status()
            return str(status.get("active_provider") or "MOCK")
        return "MOCK"

    def _run_safe_execution_bridge(
        self,
        decision_log: DecisionModel,
        chief_decision: dict[str, Any],
    ) -> dict[str, Any]:
        if self._execution_bridge is None:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Chief execution bridge is not configured.",
            }
        try:
            return dict(
                self._execution_bridge.execute_chief_decision_if_safe(
                    decision_log,
                    strategy_side=str(chief_decision.get("final_action") or "HOLD"),
                ),
            )
        except Exception as exc:
            self._state.set_last_error(str(exc))
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": f"Chief execution bridge error: {exc}",
            }

    def _decision_with_bridge_result(
        self,
        decision: DecisionModel,
        bridge_result: dict[str, Any],
    ) -> DecisionModel:
        brain = dict(decision.brain or {})
        brain["execution_bridge"] = bridge_result
        skip_reason = bridge_result.get("skip_reason")
        explanation = decision.explanation
        if skip_reason:
            explanation = f"{explanation} Chief bridge did not open a trade: {skip_reason}."
        elif bridge_result.get("executed"):
            explanation = (
                f"{explanation} Chief bridge opened demo/paper trade "
                f"{bridge_result.get('opened_trade_id')}."
            )
        return decision.model_copy(
            update={
                "brain": brain,
                "explanation": explanation,
            },
        )
