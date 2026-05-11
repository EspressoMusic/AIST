"""Orchestrates one bot cycle — paper demo or Spot Testnet orders (never mainnet)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.agents import (
    debate_agent,
    decision_coordinator,
    execution_agent,
    execution_gate,
    learning_agent,
    market_data_agent,
    news_agent,
    risk_agent,
    technical_agent,
)
from app.config import Settings
from app.demo_bot_constants import (
    ALLOWED_BOT_TESTNET_SYMBOLS,
    DEMO_CONFIDENCE_THRESHOLD,
    DEMO_MAX_ORDER_USDT,
    DEMO_RISK_SCORE_THRESHOLD,
    EXEC_GATE_DAILY_MAX_LOSS_USDT,
    EXEC_GATE_MAX_OPENS_PER_DAY,
    MAX_OPEN_POSITIONS,
    TESTNET_DEV_MAX_CYCLES_OPEN,
    TESTNET_DEV_SL_PCT,
    TESTNET_DEV_TP_PCT,
    TESTNET_MARKET_BUY_QUOTE_USDT,
    TRADE_SOURCE_BINANCE_TESTNET,
    TRADE_SOURCE_PAPER_DEMO,
)
from app.models.bot_api_model import ForceCloseResponse, ForceDemoTradeResponse
from app.models.cycle_model import BotCycleResultModel
from app.models.decision_model import DecisionModel
from app.models.demo_trade import (
    DemoTrade,
    demo_pnl_fraction,
    demo_realized_pnl_at_close,
    demo_unrealized_pnl,
)
from app.models.execution_mode import ExecutionMode
from app.models.testnet_order_record import TestnetOrderRecord
from app.models.testnet_position import TestnetTrackedPosition
from app.services.binance_testnet_service import BinanceTestnetService
from app.services.ai_provider_service import AIProviderService
from app.services.bot_state_service import BotStateService
from app.services.demo_price_display import demo_display_price_map
from app.services.exchange_service import ExchangeService
from app.services.news_source_service import NewsSourceService
from app.services.performance_service import build_performance_response
from app.services.testnet_strategy_engine import build_testnet_entry_packet

logger = logging.getLogger(__name__)

_TP_FRAC = 0.01  # +1.0% take-profit
_SL_FRAC = 0.005  # -0.5% stop-loss (loss magnitude)
_MAX_CYCLES_OPEN = 6

_REJ_MAX_OPEN = "Max open trades reached"
_REJ_MAX_TESTNET = "Max testnet positions reached"
_REJ_DUP_SYMBOL = "Symbol already open"
_REJ_CONFIDENCE = "Confidence too low"
_REJ_RISK_SCORE = "Risk score too low"
_REJ_RISK = "Risk rejected"
_REJ_STRATEGY_HOLD = "Strategy chose HOLD"
_REJ_NO_TESTNET_POSITION = "No testnet position to sell"
_REJ_TESTNET_SYMBOL = "Symbol not allowed for bot testnet trading"
_REJ_AUTONOMY_DISABLED = "Chief demo autonomy is disabled"
_REJ_ALPACA_NOT_WIRED = "ALPACA_PAPER manual endpoints are available; bot engine execution is not wired yet"


def _cumulative_quote_from_binance_response(raw: dict[str, Any]) -> float:
    """
    Quote filled (USDT) from Binance order JSON.

    Uses ``cummulativeQuoteQty`` (Binance spelling), ``cumulativeQuoteQty``, or sums ``fills``.
    """
    v = raw.get("cummulativeQuoteQty")
    if v is None:
        v = raw.get("cumulativeQuoteQty")
    cq = float(v or 0.0)
    if cq > 0:
        return cq

    fills = raw.get("fills")
    if isinstance(fills, list):
        total = 0.0
        for row in fills:
            if isinstance(row, dict):
                q = float(row.get("qty") or 0.0)
                p = float(row.get("price") or 0.0)
                total += q * p
        if total > 0:
            return total

    ex_qty = float(raw.get("executedQty") or 0.0)
    avg_px = raw.get("avgPrice") or raw.get("price")
    if ex_qty > 0 and avg_px is not None:
        ap = float(avg_px)
        if ap > 0:
            return ex_qty * ap
    return 0.0


def _prefer_binance_get_order_quote(
    binance: BinanceTestnetService,
    symbol: str,
    post_raw: dict[str, Any],
) -> dict[str, Any]:
    """
    After POST /v3/order, reconcile cumulative quote via GET /v3/order.

    Spot Testnet sometimes returns incomplete quote totals on the POST body immediately;
    using the FILLED query result avoids bogus realized P/L (e.g. large UI profit vs tiny loss).
    """
    oid = int(post_raw.get("orderId") or 0)
    if oid <= 0:
        return post_raw
    sym_u = symbol.strip().upper()
    post_cq = _cumulative_quote_from_binance_response(post_raw)
    try:
        fetched = binance.get_order(sym_u, oid)
        if not isinstance(fetched, dict):
            return post_raw
        st = str(fetched.get("status") or "").upper()
        get_cq = _cumulative_quote_from_binance_response(fetched)
        if st == "FILLED" and get_cq > 0:
            if abs(get_cq - post_cq) > 1e-8:
                logger.info(
                    "Binance Testnet %s orderId=%s: POST cumulativeQuote≈%.10f → GET %.10f",
                    sym_u,
                    oid,
                    post_cq,
                    get_cq,
                )
            return fetched
        if get_cq > post_cq > 0:
            return fetched
    except Exception as exc:
        logger.warning(
            "Binance Testnet GET /order failed for %s orderId=%s: %s",
            sym_u,
            oid,
            exc,
        )
    return post_raw


def _record_from_binance_order(
    raw: dict[str, Any],
    *,
    client_tag: str,
    error_message: str | None = None,
) -> TestnetOrderRecord:
    oid = int(raw.get("orderId") or 0)
    sym = str(raw.get("symbol") or "")
    status = str(raw.get("status") or "")
    side = str(raw.get("side") or "")
    ex_qty = float(raw.get("executedQty") or 0)
    cq = _cumulative_quote_from_binance_response(raw)
    avg = (cq / ex_qty) if ex_qty > 0 and cq > 0 else None
    return TestnetOrderRecord(
        symbol=sym,
        side=side,
        order_id=oid,
        status=status,
        executed_qty=ex_qty,
        cumulative_quote_qty=cq,
        avg_price=avg,
        created_at=datetime.now(timezone.utc),
        client_tag=client_tag,
        error_message=error_message,
    )


class BotEngineService:
    def __init__(
        self,
        *,
        exchange: ExchangeService,
        state: BotStateService,
        binance_testnet: BinanceTestnetService,
        settings: Settings,
        ai_provider: AIProviderService,
        news_source: NewsSourceService,
    ) -> None:
        self._exchange = exchange
        self._state = state
        self._binance = binance_testnet
        self._settings = settings
        self._ai = ai_provider
        self._news_source = news_source

    def run_one_cycle(self) -> BotCycleResultModel:
        tick_seq = self._state.next_demo_price_tick_seq()
        raw = self._exchange.get_prices()
        price_map = demo_display_price_map(raw, tick_seq)

        closed_ids = self._update_open_prices_and_maybe_close(price_map)
        if self._state.execution_mode == ExecutionMode.BINANCE_TESTNET:
            closed_ids = [*closed_ids, *self._maybe_auto_close_binance_testnet()]

        symbol = self._pick_symbol()
        mid = price_map[symbol]

        seed_hint = float(len(self._state.decisions_newest_first()))
        performance = build_performance_response(self._state)
        streak = self._state.consecutive_closed_losses(symbol)
        dd_proxy = self._state.drawdown_proxy()
        snap = self._state.exec_gate_snapshot()

        market = market_data_agent.collect(symbol, mid, price_map, tick_hint=seed_hint)
        news = news_agent.analyze(
            symbol,
            seed_hint=seed_hint,
            ai_client=self._ai,
            news_source=self._news_source,
        )
        technical = technical_agent.analyze(
            symbol,
            mid,
            market_payload=market.payload,
            ai_client=self._ai,
        )
        vol_hint = None
        if isinstance(market.payload, dict):
            vol_hint = market.payload.get("realized_vol_short")

        risk = risk_agent.evaluate(
            symbol,
            news_score=news.score,
            technical_score=technical.score,
            open_positions=self._state.effective_open_positions_for_risk(),
            market_volatility=float(vol_hint) if vol_hint is not None else None,
            consecutive_losses_symbol=streak,
            exec_gate_pnl_today=float(snap.get("realized_pnl_today") or 0.0),
            drawdown_proxy=dd_proxy,
            ai_client=self._ai,
        )
        learning = learning_agent.analyze_pipeline(
            symbol,
            lessons_recent_count=self._state.lessons_count(),
            seed_mod=seed_hint,
            performance=performance,
            consecutive_losses_symbol=streak,
            drawdown_proxy=dd_proxy,
            ai_client=self._ai,
        )
        debate = debate_agent.deliberate(
            symbol,
            market=market,
            technical=technical,
            news=news,
            risk=risk,
            learning=learning,
            execution_mode=self._state.execution_mode,
            ai_client=self._ai,
        )

        decision = decision_coordinator.compose_from_brain(
            symbol,
            market=market,
            technical=technical,
            news=news,
            risk=risk,
            learning=learning,
            debate=debate,
        )

        _, gate_diag, gate_agent = execution_gate.evaluate_gate(
            settings=self._settings,
            state=self._state,
            decision=decision,
            proposed_action=debate.action or "HOLD",
        )
        _brain = dict(decision.brain or {})
        _brain["execution_gate"] = gate_diag
        decision = decision.model_copy(update={"brain": _brain})

        mode = self._state.execution_mode
        intended_action = debate.action or "HOLD"
        if (
            mode == ExecutionMode.BINANCE_TESTNET
            and intended_action == "BUY"
            and decision.final_action == "BUY"
        ):
            pkt = build_testnet_entry_packet(
                symbol=decision.symbol,
                binance=self._binance,
                state=self._state,
                confidence=decision.confidence,
                risk_score=decision.risk_score,
            )
            decision = decision.model_copy(update={"testnet_entry": pkt})

        opened_id: str | None = None
        skip_reason = self._open_rejection_reason(decision, strategy_side=intended_action)
        self._state.set_last_open_skipped_reason(skip_reason)

        exec_extra = ""

        if skip_reason is None:
            if mode == ExecutionMode.PAPER_DEMO:
                opened_id = self._open_demo_trade(decision, mid)
            elif mode == ExecutionMode.BINANCE_TESTNET:
                opened_id, skip_reason, tn_closed, exec_extra = (
                    self._execute_binance_testnet(decision, price_map)
                )
                closed_ids = [*closed_ids, *tn_closed]
            else:
                skip_reason = _REJ_ALPACA_NOT_WIRED
            if opened_id is not None:
                self._state.exec_gate_on_successful_open()

        decision_to_record = decision
        if skip_reason is not None:
            decision_to_record = decision.model_copy(
                update={
                    "explanation": (
                        f"{decision.explanation} Trade not opened: {skip_reason}."
                    ),
                },
            )

        exec_summary = execution_agent.summarize_execution(
            symbol,
            opened=opened_id is not None,
            closed_ids=closed_ids,
            skip_reason=skip_reason,
            execution_mode=mode,
            extra_detail=exec_extra,
        )

        agents_ordered = [
            market,
            technical,
            news,
            risk,
            learning,
            debate,
            gate_agent,
            exec_summary,
        ]

        cycle = BotCycleResultModel(
            decision=decision_to_record,
            agents=agents_ordered,
            attempted_symbol=symbol,
            intended_action=intended_action,
            opened_trade_id=opened_id,
            closed_trade_ids=closed_ids,
            open_skipped_reason=skip_reason,
        )

        self._state.append_decision(decision_to_record)
        self._state.set_latest_agents(agents_ordered)
        self._state.set_last_cycle(cycle)

        logger.info(
            "Cycle %s mode=%s action=%s opened=%s skip=%s closed=%s",
            symbol,
            mode.value,
            decision.final_action,
            opened_id,
            skip_reason,
            closed_ids,
        )
        return cycle

    def _symbol_blocked_for_new_trade(self, symbol: str) -> bool:
        if self._state.execution_mode == ExecutionMode.BINANCE_TESTNET:
            return self._state.testnet_has_open_on_symbol(symbol)
        return self._symbol_has_open_trade(symbol)

    def _open_rejection_reason(
        self,
        decision: DecisionModel,
        *,
        strategy_side: str,
    ) -> str | None:
        wants_trade = strategy_side in ("BUY", "SELL")
        if not wants_trade:
            return _REJ_STRATEGY_HOLD

        if decision.final_action not in ("BUY", "SELL"):
            if not decision.risk_approved:
                return _REJ_RISK
            return None

        mode = self._state.execution_mode
        if mode == ExecutionMode.ALPACA_PAPER:
            return _REJ_ALPACA_NOT_WIRED
        demo_week_reason = self._state.demo_week_blocked_reason(
            order_usdt=TESTNET_MARKET_BUY_QUOTE_USDT,
        )
        if demo_week_reason is not None and strategy_side == "BUY":
            return demo_week_reason

        br = decision.brain or {}
        eg = br.get("execution_gate") if isinstance(br, dict) else None
        if (
            isinstance(eg, dict)
            and eg.get("allowed") is False
            and strategy_side == "BUY"
            and decision.final_action == "BUY"
        ):
            return str(eg.get("reason") or "Execution gate blocked open.")

        if (
            mode == ExecutionMode.BINANCE_TESTNET
            and decision.symbol not in ALLOWED_BOT_TESTNET_SYMBOLS
        ):
            return _REJ_TESTNET_SYMBOL

        if mode == ExecutionMode.BINANCE_TESTNET:
            if strategy_side == "SELL":
                if not self._state.testnet_has_open_on_symbol(decision.symbol):
                    return _REJ_NO_TESTNET_POSITION
            elif strategy_side == "BUY":
                if self._state.testnet_any_open():
                    if self._state.testnet_has_open_on_symbol(decision.symbol):
                        return _REJ_DUP_SYMBOL
                    return _REJ_MAX_TESTNET
        else:
            if self._state.open_positions_count() >= MAX_OPEN_POSITIONS:
                return _REJ_MAX_OPEN
            if self._symbol_has_open_trade(decision.symbol):
                return _REJ_DUP_SYMBOL

        if not decision.risk_approved:
            return _REJ_RISK

        if (
            mode == ExecutionMode.BINANCE_TESTNET
            and strategy_side == "BUY"
            and decision.final_action == "BUY"
        ):
            te = decision.testnet_entry
            if not isinstance(te, dict):
                return "Testnet strategy evaluation missing."
            if not te.get("passed"):
                return str(te.get("skip_reason") or "Testnet strategy gate")[:512]
            return None

        if decision.confidence < DEMO_CONFIDENCE_THRESHOLD:
            return _REJ_CONFIDENCE
        if decision.risk_score < DEMO_RISK_SCORE_THRESHOLD:
            return _REJ_RISK_SCORE
        return None

    def execute_chief_decision_if_safe(
        self,
        decision: DecisionModel,
        *,
        strategy_side: str,
    ) -> dict[str, Any]:
        """Optional Chief AI bridge. Uses existing paper/testnet open paths only."""
        if not self._state.chief_demo_autonomy_enabled():
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": _REJ_AUTONOMY_DISABLED,
            }
        if self._state.execution_mode not in {
            ExecutionMode.PAPER_DEMO,
            ExecutionMode.BINANCE_TESTNET,
        }:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Execution mode is not allowed for Chief demo autonomy.",
            }
        if self._settings.bot_kill_switch:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Kill switch is active.",
            }
        if decision.final_action != "BUY" or strategy_side != "BUY":
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Chief final action is not BUY.",
            }
        if decision.confidence < 75.0:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Chief confidence below 75.",
            }
        if self._state.effective_open_positions_for_risk() >= 1:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Open position already exists.",
            }
        snap = self._state.exec_gate_snapshot()
        if float(snap.get("realized_pnl_today") or 0.0) <= EXEC_GATE_DAILY_MAX_LOSS_USDT:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Daily loss limit reached.",
            }
        if int(snap.get("opens_today") or 0) >= EXEC_GATE_MAX_OPENS_PER_DAY:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": "Daily trade limit reached.",
            }
        cooldown_reason = self._state.testnet_buy_blocked_reason(decision.symbol)
        if cooldown_reason is not None:
            return {
                "executed": False,
                "opened_trade_id": None,
                "skip_reason": cooldown_reason,
            }
        brain = decision.brain or {}
        chief = brain.get("chief_decision") if isinstance(brain, dict) else None
        if isinstance(chief, dict):
            gate = chief.get("execution_gate")
            if isinstance(gate, dict):
                checks = gate.get("checks")
                risk_gate = checks.get("risk_gate") if isinstance(checks, dict) else None
                if isinstance(risk_gate, dict) and risk_gate.get("veto") is True:
                    return {
                        "executed": False,
                        "opened_trade_id": None,
                        "skip_reason": "Risk Agent veto is active.",
                    }

        tick_seq = self._state.next_demo_price_tick_seq()
        raw = self._exchange.get_prices()
        price_map = demo_display_price_map(raw, tick_seq)
        self._state.update_open_trade_prices(price_map)
        if self._state.execution_mode == ExecutionMode.BINANCE_TESTNET:
            decision = decision.model_copy(
                update={
                    "testnet_entry": build_testnet_entry_packet(
                        symbol=decision.symbol,
                        binance=self._binance,
                        state=self._state,
                        confidence=decision.confidence,
                        risk_score=decision.risk_score,
                    ),
                },
            )
        skip_reason = self._open_rejection_reason(decision, strategy_side=strategy_side)
        if skip_reason is not None:
            self._state.set_last_open_skipped_reason(skip_reason)
            return {"executed": False, "opened_trade_id": None, "skip_reason": skip_reason}

        opened_id: str | None = None
        closed_ids: list[str] = []
        exec_extra = ""
        if self._state.execution_mode == ExecutionMode.PAPER_DEMO:
            mid = float(price_map.get(decision.symbol) or 0.0)
            opened_id = self._open_demo_trade(decision, mid)
        else:
            opened_id, skip_reason, closed_ids, exec_extra = self._execute_binance_testnet(
                decision,
                price_map,
            )
        if opened_id is not None:
            self._state.exec_gate_on_successful_open()
        self._state.set_last_open_skipped_reason(skip_reason)
        return {
            "executed": opened_id is not None,
            "opened_trade_id": opened_id,
            "skip_reason": skip_reason,
            "closed_trade_ids": closed_ids,
            "execution_detail": exec_extra,
        }

    def _finalize_binance_testnet_market_sell(
        self,
        *,
        removed: DemoTrade,
        sell_raw: dict[str, Any],
        sell_rec: TestnetOrderRecord,
        trade_reason: str,
        buy_quote_basis: float,
        trade_id: str,
    ) -> None:
        """
        Single finalize path for every Spot Testnet MARKET SELL that closes a DemoTrade.

        Realized P/L uses Binance quote totals when available:
        ``sell_cummulative_quote_qty - buy_cummulative_quote_qty`` (positive iff proceeds exceed cost).
        BUY and SELL cumulative quotes are re-read via ``GET /v3/order`` when needed so totals match
        the exchange (POST bodies can be incomplete on Testnet).
        If either quote total is still missing/zero, falls back to
        ``(exit_price - entry_price) * quantity`` for BUY-sided trades.
        ``buy_quote_basis`` is ``position.quote_spent`` from the opening BUY (backup).
        """
        sym_ord = str(removed.symbol).strip().upper()
        binance_ok = (
            self._settings.use_binance_testnet and self._binance.is_configured
        )

        sell_cq = _cumulative_quote_from_binance_response(sell_raw)
        if sell_cq <= 0:
            sell_cq = float(sell_rec.cumulative_quote_qty or 0.0)

        sell_oid = int(sell_rec.order_id or 0)
        if binance_ok and sell_cq <= 0 and sell_oid > 0:
            try:
                sr = self._binance.get_order(sym_ord, sell_oid)
                if isinstance(sr, dict):
                    sq = _cumulative_quote_from_binance_response(sr)
                    if sq > 0:
                        sell_cq = sq
                        logger.info(
                            "Binance Testnet finalize: SELL cq repaired via GET "
                            "orderId=%s cq=%.10f",
                            sell_oid,
                            sell_cq,
                        )
            except Exception as exc:
                logger.warning("Binance Testnet GET SELL order in finalize: %s", exc)

        ex_qty = float(sell_raw.get("executedQty") or sell_rec.executed_qty or 0.0)

        exit_avg = float(sell_rec.avg_price or 0.0)
        if exit_avg <= 0 and ex_qty > 0 and sell_cq > 0:
            exit_avg = sell_cq / ex_qty
        if exit_avg <= 0:
            exit_avg = float(removed.entry_price)

        buy_cq = removed.buy_quote_cost
        if buy_cq is None or float(buy_cq) <= 0:
            buy_cq = float(buy_quote_basis)
        if float(buy_cq) <= 0:
            buy_cq = float(buy_quote_basis)

        oid_buy = removed.binance_order_id
        if binance_ok and oid_buy is not None and int(oid_buy) > 0:
            try:
                br = self._binance.get_order(sym_ord, int(oid_buy))
                if isinstance(br, dict):
                    bq = _cumulative_quote_from_binance_response(br)
                    if bq > 0:
                        prev = float(buy_cq)
                        buy_cq = bq
                        if abs(prev - bq) > 1e-6:
                            logger.info(
                                "Binance Testnet finalize: BUY cq from exchange "
                                "orderId=%s cq=%.10f (tracker had %.10f)",
                                oid_buy,
                                bq,
                                prev,
                            )
            except Exception as exc:
                logger.warning(
                    "Binance Testnet GET BUY order in finalize trade=%s: %s",
                    trade_id,
                    exc,
                )

        if float(buy_cq) > 0:
            removed.buy_quote_cost = float(buy_cq)
        elif removed.buy_quote_cost is None and float(buy_quote_basis) > 0:
            removed.buy_quote_cost = float(buy_quote_basis)

        if float(sell_cq) > 0:
            removed.sell_quote_proceeds = float(sell_cq)

        removed.exit_price = exit_avg
        removed.current_price = exit_avg
        removed.sell_order_id = int(sell_rec.order_id)
        removed.is_open = False
        removed.closed_at = datetime.now(timezone.utc)
        removed.reason = trade_reason

        if sell_cq > 0 and buy_cq > 0:
            removed.profit_loss = float(sell_cq) - float(buy_cq)
        else:
            removed.profit_loss = demo_realized_pnl_at_close(
                removed,
                exit_price=exit_avg,
            )
            logger.warning(
                "Binance Testnet P/L fallback price×qty (missing quote totals): "
                "sell_cq=%s buy_cq=%s trade=%s",
                sell_cq,
                buy_cq,
                trade_id,
            )

        logger.info(
            "Binance Testnet close finalized trade=%s entry_price=%.10f exit_price=%.10f "
            "quantity=%.10f buy_cummulative_quote_qty=%.10f sell_cummulative_quote_qty=%.10f "
            "calculated_profit_loss=%.10f close_reason=%s buy_order_id=%s sell_order_id=%s",
            trade_id,
            removed.entry_price,
            exit_avg,
            removed.quantity,
            float(buy_cq),
            float(sell_cq),
            removed.profit_loss,
            trade_reason,
            removed.binance_order_id,
            removed.sell_order_id,
        )

    def _execute_binance_testnet_market_sell(
        self,
        sym: str,
        pos: TestnetTrackedPosition,
        *,
        trade_reason: str,
        client_tag: str,
    ) -> tuple[list[str], str | None]:
        """Place Spot Testnet MARKET SELL, finalize DemoTrade, clear tracked position."""
        closed: list[str] = []
        sym_u = sym.strip().upper()
        if not self._settings.use_binance_testnet or not self._binance.is_configured:
            msg = "Binance Testnet not configured (keys / USE_BINANCE_TESTNET)."
            logger.warning("Binance Testnet sell skipped: %s", msg)
            return closed, msg

        trade_id = pos.demo_trade_id
        removed = self._state.remove_open(trade_id)
        if removed is None:
            msg = f"Open demo trade {trade_id} missing; Spot SELL not sent."
            logger.warning("Binance Testnet SELL aborted: %s", msg)
            self._state.testnet_clear_position()
            return closed, msg
        if removed.source != TRADE_SOURCE_BINANCE_TESTNET:
            self._state.add_open_trade(removed)
            msg = "Open trade is not BINANCE_TESTNET; sell aborted."
            logger.warning("%s", msg)
            return closed, msg

        quote_basis = float(pos.quote_spent)

        try:
            raw = self._binance.place_market_sell(sym_u, pos.base_quantity)
            raw = _prefer_binance_get_order_quote(self._binance, sym_u, raw)
            rec = _record_from_binance_order(raw, client_tag=client_tag)
            self._state.append_testnet_order(rec)

            self._finalize_binance_testnet_market_sell(
                removed=removed,
                sell_raw=raw,
                sell_rec=rec,
                trade_reason=trade_reason,
                buy_quote_basis=quote_basis,
                trade_id=trade_id,
            )

            self._state.push_history(removed)
            self._state.append_lesson(
                learning_agent.lesson_from_closed_trade(removed),
            )
            self._state.testnet_clear_position()
            closed.append(f"tn-close-{trade_id}")

            return closed, None
        except Exception as exc:
            logger.warning("Binance testnet SELL failed: %s", exc)
            err = str(exc)
            self._state.add_open_trade(removed)
            self._state.testnet_set_position(pos)
            self._state.append_testnet_order(
                TestnetOrderRecord(
                    symbol=sym_u,
                    side="SELL",
                    order_id=0,
                    status="ERROR",
                    executed_qty=0.0,
                    cumulative_quote_qty=0.0,
                    avg_price=None,
                    created_at=datetime.now(timezone.utc),
                    client_tag=f"{client_tag}_error",
                    error_message=err,
                ),
            )
            return closed, err

    def _maybe_auto_close_binance_testnet(self) -> list[str]:
        """BINANCE_TESTNET only: fast TP / SL / max-holding exits via real MARKET SELL."""
        if self._state.execution_mode != ExecutionMode.BINANCE_TESTNET:
            return []

        pos = self._state.testnet_tracked_position()
        if pos is None:
            return []

        trade = self._state.snapshot_open_trades().get(pos.demo_trade_id)
        if trade is None or trade.source != TRADE_SOURCE_BINANCE_TESTNET:
            return []

        # Align MTM with Spot Testnet last price (demo jitter/main feed can lag Binance UI).
        try:
            live_px = self._binance.get_testnet_last_price(trade.symbol)
            trade.current_price = float(live_px)
            trade.profit_loss = float(demo_unrealized_pnl(trade))
        except Exception as exc:
            logger.warning(
                "Binance Testnet ticker refresh failed for %s (%s); "
                "using last engine price for exit rules.",
                trade.symbol,
                exc,
            )

        trade.demo_cycles_open += 1

        entry = float(trade.entry_price)
        if entry > 0 and trade.side.lower() == "buy":
            pnl_percent = (float(trade.current_price) - entry) / entry * 100.0
        elif entry > 0:
            pnl_percent = (entry - float(trade.current_price)) / entry * 100.0
        else:
            pnl_percent = 0.0

        exit_kind: str | None = None
        exit_rule_status = "hold"
        if pnl_percent >= TESTNET_DEV_TP_PCT:
            exit_kind = "take profit"
            exit_rule_status = "take_profit_triggered"
        elif pnl_percent <= TESTNET_DEV_SL_PCT:
            exit_kind = "stop loss"
            exit_rule_status = "stop_loss_triggered"
        elif trade.demo_cycles_open >= TESTNET_DEV_MAX_CYCLES_OPEN:
            exit_kind = "max cycles reached"
            exit_rule_status = "max_cycles_triggered"

        logger.info(
            "Binance Testnet position monitor trade=%s entry=%.8f current=%.8f qty=%.8f "
            "profit_loss=%.8f pnl_percent=%.6f%% cycles_open=%s exit_rule=%s "
            "(thresholds: TP>=%s%% SL<=%s%% max_cycles=%s)",
            trade.id,
            trade.entry_price,
            trade.current_price,
            trade.quantity,
            trade.profit_loss,
            pnl_percent,
            trade.demo_cycles_open,
            exit_rule_status,
            TESTNET_DEV_TP_PCT,
            TESTNET_DEV_SL_PCT,
            TESTNET_DEV_MAX_CYCLES_OPEN,
        )

        if exit_kind is None:
            return []

        logger.info(
            "Binance Testnet auto-exit firing trade=%s trigger=%s pnl_percent=%.6f%%",
            trade.id,
            exit_kind,
            pnl_percent,
        )

        if exit_kind == "take profit":
            reason = (
                "Closed Binance Testnet trade because take profit reached "
                f"(pnl_percent >= +{TESTNET_DEV_TP_PCT:.2f}% vs entry; Spot Testnet only)."
            )
        elif exit_kind == "stop loss":
            reason = (
                "Closed Binance Testnet trade because stop loss reached "
                f"(pnl_percent <= {TESTNET_DEV_SL_PCT:.2f}% vs entry; Spot Testnet only)."
            )
        else:
            reason = (
                "Closed Binance Testnet trade because max cycles reached "
                f"({TESTNET_DEV_MAX_CYCLES_OPEN} ticks, Spot Testnet dev exit only)."
            )

        closed, sell_err = self._execute_binance_testnet_market_sell(
            pos.symbol,
            pos,
            trade_reason=reason,
            client_tag="bot_market_sell_auto_exit",
        )
        if sell_err:
            logger.warning(
                "Binance Testnet auto-exit sell failed (%s); position stays open.",
                sell_err,
            )
            return []
        return closed

    def _execute_binance_testnet(
        self,
        decision: DecisionModel,
        price_map: dict[str, float],
    ) -> tuple[str | None, str | None, list[str], str]:
        """Returns opened_ref, skip_reason, testnet_close_ids, execution_agent_extra."""
        sym = decision.symbol.strip().upper()
        closed: list[str] = []
        extra = ""

        if decision.final_action == "BUY":
            if not self._settings.use_binance_testnet or not self._binance.is_configured:
                return (
                    None,
                    "Binance Testnet not configured (keys / USE_BINANCE_TESTNET).",
                    [],
                    "",
                )
            try:
                raw = self._binance.place_market_buy(sym, TESTNET_MARKET_BUY_QUOTE_USDT)
                raw = _prefer_binance_get_order_quote(self._binance, sym, raw)
                rec = _record_from_binance_order(raw, client_tag="bot_market_buy")
                self._state.append_testnet_order(rec)
                oid = rec.order_id
                qty = rec.executed_qty
                if qty <= 0:
                    msg = "Testnet BUY reported zero executedQty."
                    fail_rec = TestnetOrderRecord(
                        symbol=sym,
                        side="BUY",
                        order_id=oid,
                        status=rec.status,
                        executed_qty=qty,
                        cumulative_quote_qty=rec.cumulative_quote_qty,
                        avg_price=rec.avg_price,
                        created_at=datetime.now(timezone.utc),
                        client_tag="bot_market_buy_error",
                        error_message=msg,
                    )
                    self._state.append_testnet_order(fail_rec)
                    return None, f"Testnet order failed: {msg}", [], msg

                buy_cq = _cumulative_quote_from_binance_response(raw)
                if buy_cq <= 0:
                    buy_cq = float(rec.cumulative_quote_qty or 0.0)

                avg_px = float(rec.avg_price or 0.0)
                if avg_px <= 0 and qty > 0 and buy_cq > 0:
                    avg_px = buy_cq / qty
                if avg_px <= 0:
                    ap_raw = raw.get("avgPrice") or raw.get("price")
                    if ap_raw is not None:
                        avg_px = float(ap_raw)
                try:
                    mark_px = float(self._binance.get_testnet_last_price(sym))
                except Exception:
                    mark_px = float(price_map.get(sym, avg_px))
                if buy_cq <= 0 and qty > 0 and avg_px > 0:
                    buy_cq = qty * avg_px

                now = datetime.now(timezone.utc)
                trade_id = self._state.next_trade_id()
                trade = DemoTrade(
                    id=trade_id,
                    symbol=sym,
                    side="Buy",
                    entry_price=avg_px,
                    current_price=mark_px,
                    quantity=qty,
                    profit_loss=0.0,
                    opened_at=now,
                    closed_at=None,
                    is_open=True,
                    reason="Opened by Binance Testnet order",
                    demo_cycles_open=0,
                    source=TRADE_SOURCE_BINANCE_TESTNET,
                    binance_order_id=oid,
                    sell_order_id=None,
                    exit_price=None,
                    buy_quote_cost=float(buy_cq) if buy_cq > 0 else None,
                    sell_quote_proceeds=None,
                )
                trade.profit_loss = demo_unrealized_pnl(trade)
                self._state.add_open_trade(trade)

                quote_spent = float(buy_cq) if buy_cq > 0 else float(rec.cumulative_quote_qty or 0.0)
                self._state.testnet_set_position(
                    TestnetTrackedPosition(
                        symbol=sym,
                        base_quantity=qty,
                        quote_spent=quote_spent,
                        entry_order_id=oid,
                        opened_at=now,
                        demo_trade_id=trade_id,
                    ),
                )
                logger.info(
                    "Opened Binance Testnet trade with %s USDT test order "
                    "(Spot Testnet only — no real money).",
                    TESTNET_MARKET_BUY_QUOTE_USDT,
                )
                return trade_id, None, [], ""
            except Exception as exc:
                logger.warning("Binance testnet BUY failed: %s", exc)
                err = str(exc)
                self._state.append_testnet_order(
                    TestnetOrderRecord(
                        symbol=sym,
                        side="BUY",
                        order_id=0,
                        status="ERROR",
                        executed_qty=0.0,
                        cumulative_quote_qty=0.0,
                        avg_price=None,
                        created_at=datetime.now(timezone.utc),
                        client_tag="bot_market_buy_error",
                        error_message=err,
                    ),
                )
                extra = f"Testnet BUY error logged (no retry)."
                return None, f"Testnet order failed: {err}", [], extra

        if decision.final_action == "SELL":
            pos = self._state.testnet_tracked_position()
            if pos is None or pos.symbol != sym:
                return None, _REJ_NO_TESTNET_POSITION, [], ""

            closed_sel, sell_err = self._execute_binance_testnet_market_sell(
                sym,
                pos,
                trade_reason=(
                    "Closed by Binance Testnet order (strategy SELL signal). "
                    "Spot Testnet only — no real money."
                ),
                client_tag="bot_market_sell",
            )
            closed.extend(closed_sel)
            if sell_err:
                extra = "Testnet SELL error logged (no retry)."
                return None, f"Testnet order failed: {sell_err}", closed, extra
            return None, None, closed, ""

        return None, None, [], ""

    def _symbol_has_open_trade(self, symbol: str) -> bool:
        for t in self._state.snapshot_open_trades().values():
            if t.symbol == symbol and t.is_open:
                return True
        return False

    def _pick_symbol(self) -> str:
        return "BTCUSDT" if len(self._state.decisions_newest_first()) % 2 == 0 else "ETHUSDT"

    def _spawn_demo_trade(
        self,
        symbol: str,
        mid: float,
        *,
        final_action: str,
        trade_reason: str | None = None,
    ) -> str | None:
        if final_action not in ("BUY", "SELL"):
            return None
        qty = 0.002 if symbol == "BTCUSDT" else 0.02
        side = "Buy" if final_action == "BUY" else "Sell"
        trade_id = self._state.next_trade_id()
        now = datetime.now(timezone.utc)
        trade = DemoTrade(
            id=trade_id,
            symbol=symbol,
            side=side,
            entry_price=mid,
            current_price=mid,
            quantity=qty,
            profit_loss=0.0,
            opened_at=now,
            closed_at=None,
            is_open=True,
            reason=trade_reason or "Opened by demo execution agent (simulated).",
            demo_cycles_open=0,
            source=TRADE_SOURCE_PAPER_DEMO,
            binance_order_id=None,
            sell_order_id=None,
        )
        trade.profit_loss = demo_unrealized_pnl(trade)
        self._state.add_open_trade(trade)
        return trade_id

    def _open_demo_trade(self, decision: DecisionModel, mid: float) -> str | None:
        return self._spawn_demo_trade(
            decision.symbol,
            mid,
            final_action=decision.final_action,
        )

    def _update_open_prices_and_maybe_close(self, price_map: dict[str, float]) -> list[str]:
        self._state.update_open_trade_prices(price_map)
        closed: list[str] = []
        for tid, trade in list(self._state.snapshot_open_trades().items()):
            if trade.source == TRADE_SOURCE_BINANCE_TESTNET:
                continue
            trade.demo_cycles_open += 1
            move = demo_pnl_fraction(trade)
            reason = ""
            if move >= _TP_FRAC:
                reason = "Demo take-profit (+1.0%)."
            elif move <= -_SL_FRAC:
                reason = "Demo stop-loss (-0.5%)."
            elif trade.demo_cycles_open >= _MAX_CYCLES_OPEN:
                reason = "Demo max holding (6 ticks)."

            if reason:
                exit_px = float(trade.current_price)
                trade.is_open = False
                trade.closed_at = datetime.now(timezone.utc)
                trade.exit_price = exit_px
                trade.profit_loss = demo_realized_pnl_at_close(
                    trade,
                    exit_price=exit_px,
                )
                trade.reason = reason
                removed = self._state.remove_open(tid)
                if removed:
                    self._state.push_history(removed)
                    self._state.append_lesson(
                        learning_agent.lesson_from_closed_trade(removed),
                    )
                closed.append(tid)

        return closed

    def force_demo_trade(self, symbol: str | None = None) -> ForceDemoTradeResponse:
        """Open one simulated BUY if capacity allows (UI testing only)."""
        if self._state.execution_mode != ExecutionMode.PAPER_DEMO:
            return ForceDemoTradeResponse(
                opened_trade_id=None,
                attempted_symbol="BTCUSDT",
                open_skipped_reason="PAPER_DEMO mode required",
                message="Switch execution mode to PAPER_DEMO to force a simulated trade.",
            )

        tick_seq = self._state.next_demo_price_tick_seq()
        raw_prices = self._exchange.get_prices()
        price_map = demo_display_price_map(raw_prices, tick_seq)
        self._state.update_open_trade_prices(price_map)
        if symbol and symbol.upper() in price_map:
            sym_u = symbol.upper()
            order = [sym_u] + [s for s in price_map if s != sym_u]
        else:
            order = list(price_map.keys())

        if self._state.open_positions_count() >= MAX_OPEN_POSITIONS:
            return ForceDemoTradeResponse(
                opened_trade_id=None,
                attempted_symbol=order[0],
                open_skipped_reason=_REJ_MAX_OPEN,
                message="Max open trades reached; no forced demo trade opened.",
            )

        for sym in order:
            if self._symbol_has_open_trade(sym):
                continue
            tid = self._spawn_demo_trade(
                sym,
                price_map[sym],
                final_action="BUY",
                trade_reason="POST /bot/force-demo-trade — paper BUY for UI testing (no exchange).",
            )
            if tid:
                return ForceDemoTradeResponse(
                    opened_trade_id=tid,
                    attempted_symbol=sym,
                    open_skipped_reason=None,
                    message=f"Forced paper BUY on {sym}; id={tid}. No exchange orders.",
                )

        return ForceDemoTradeResponse(
            opened_trade_id=None,
            attempted_symbol=order[0],
            open_skipped_reason=_REJ_DUP_SYMBOL,
            message="All candidate symbols already have an open demo trade.",
        )

    def force_close_open_position(self) -> ForceCloseResponse:
        """POST /bot/force-close — paper closes simulated legs; testnet sends MARKET SELL once."""
        mode = self._state.execution_mode

        if mode == ExecutionMode.PAPER_DEMO:
            opens = list(self._state.snapshot_open_trades().items())
            if not opens:
                return ForceCloseResponse(
                    status="noop",
                    message="No open position to close.",
                )
            closed_ids: list[str] = []
            now = datetime.now(timezone.utc)
            for tid, trade in opens:
                exit_px = float(trade.current_price)
                trade.exit_price = exit_px
                trade.profit_loss = demo_realized_pnl_at_close(trade, exit_price=exit_px)
                trade.is_open = False
                trade.closed_at = now
                trade.reason = "Force-closed via POST /bot/force-close (paper demo)."
                removed = self._state.remove_open(tid)
                if removed:
                    self._state.push_history(removed)
                    self._state.append_lesson(
                        learning_agent.lesson_from_closed_trade(removed),
                    )
                    closed_ids.append(tid)
            logger.info("Paper force-close removed trades %s", closed_ids)
            return ForceCloseResponse(
                status="closed",
                message=f"Closed {len(closed_ids)} paper demo open trade(s).",
                closed_trade_ids=closed_ids,
            )

        pos = self._state.testnet_tracked_position()
        if pos is None:
            for tid, t in list(self._state.snapshot_open_trades().items()):
                if not t.is_open or t.source != TRADE_SOURCE_BINANCE_TESTNET:
                    continue
                base_q = float(t.quantity or 0.0)
                if base_q <= 0:
                    continue
                pos = TestnetTrackedPosition(
                    symbol=str(t.symbol).strip().upper(),
                    base_quantity=base_q,
                    quote_spent=float(t.buy_quote_cost or 0.0),
                    entry_order_id=int(t.binance_order_id or 0),
                    opened_at=t.opened_at,
                    demo_trade_id=tid,
                )
                self._state.testnet_set_position(pos)
                logger.warning(
                    "Recovered TestnetTrackedPosition from open trade %s "
                    "(tracker was missing; force-close will send MARKET SELL).",
                    tid,
                )
                break

        if pos is None:
            return ForceCloseResponse(
                status="noop",
                message="No open position to close.",
            )

        closed, sell_err = self._execute_binance_testnet_market_sell(
            pos.symbol,
            pos,
            trade_reason=(
                "Closed by POST /bot/force-close (Spot Testnet MARKET SELL; manual safety)."
            ),
            client_tag="bot_market_sell_force_close",
        )
        if sell_err:
            raise RuntimeError(sell_err)
        return ForceCloseResponse(
            status="closed",
            message="Binance Testnet position closed with MARKET SELL.",
            closed_trade_ids=closed,
        )
