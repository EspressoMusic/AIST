"""In-memory demo bot brain state."""

from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta, timezone

from app.demo_bot_constants import (
    CHIEF_DEMO_AUTONOMY_ENABLED_DEFAULT,
    DEMO_MAX_DAILY_LOSS_USDT,
    DEMO_MAX_DAILY_TRADES,
    DEMO_MAX_ORDER_USDT,
    DEMO_MAX_OPEN_POSITIONS,
    DEMO_WEEK_MODE_DEFAULT,
    TESTNET_STRATEGY_COOLDOWN_MINUTES,
    TESTNET_STRATEGY_HALT_HOURS,
    TESTNET_STRATEGY_MAX_CONSECUTIVE_LOSSES,
    TRADE_SOURCE_BINANCE_TESTNET,
)
from app.models.agent_model import AgentResultModel
from app.models.cycle_model import BotCycleResultModel
from app.models.decision_model import DecisionModel
from app.models.demo_trade import DemoTrade, demo_unrealized_pnl
from app.models.execution_mode import ExecutionMode
from app.models.lesson_model import LessonModel
from app.models.testnet_order_record import TestnetOrderRecord
from app.models.testnet_position import TestnetTrackedPosition
from app.trade_scope import trade_matches_execution_source, want_source_for_execution_mode

_MAX_DECISIONS = 80
_MAX_LESSONS = 120


class BotStateService:
    def __init__(self) -> None:
        self._started: bool = False
        self._execution_mode: ExecutionMode = ExecutionMode.BINANCE_TESTNET
        self._open_trades: dict[str, DemoTrade] = {}
        self._history: list[DemoTrade] = []
        self._decisions: deque[DecisionModel] = deque(maxlen=_MAX_DECISIONS)
        self._latest_agents: list[AgentResultModel] = []
        self._lessons: deque[LessonModel] = deque(maxlen=_MAX_LESSONS)
        self._last_cycle: BotCycleResultModel | None = None
        self._trade_seq: int = 0
        self._last_open_skipped_reason: str | None = None
        self._demo_price_tick_seq: int = 0
        self._testnet_orders: list[TestnetOrderRecord] = []
        self._testnet_position: TestnetTrackedPosition | None = None
        # Testnet strategy engine: per-symbol cooldown / loss streak / temporary halt.
        self._testnet_symbol_cooldown_until: dict[str, datetime] = {}
        self._testnet_symbol_loss_streak: dict[str, int] = {}
        self._testnet_symbol_halted_until: dict[str, datetime] = {}
        # Execution gate: UTC day rollup (any source matching current execution mode).
        self._exec_gate_day: date | None = None
        self._exec_gate_realized_pnl_today: float = 0.0
        self._exec_gate_opens_today: int = 0
        self._exec_gate_last_open_utc: datetime | None = None
        self._chief_demo_autonomy_enabled: bool = CHIEF_DEMO_AUTONOMY_ENABLED_DEFAULT
        self._last_chief_decision: dict[str, object] | None = None
        self._demo_week_enabled: bool = DEMO_WEEK_MODE_DEFAULT
        self._last_error: str | None = None

    @property
    def started(self) -> bool:
        return self._started

    def set_started(self, value: bool) -> None:
        self._started = value

    @property
    def execution_mode(self) -> ExecutionMode:
        return self._execution_mode

    def set_execution_mode(self, mode: ExecutionMode) -> None:
        self._execution_mode = mode

    def effective_open_positions_for_risk(self) -> int:
        """Positions counted toward risk agent saturation."""
        if self._execution_mode == ExecutionMode.BINANCE_TESTNET:
            return 1 if self._testnet_position is not None else 0
        return len(self._open_trades)

    def testnet_has_open_on_symbol(self, symbol: str) -> bool:
        sym = symbol.strip().upper()
        return (
            self._testnet_position is not None
            and self._testnet_position.symbol == sym
        )

    def testnet_any_open(self) -> bool:
        return self._testnet_position is not None

    def testnet_tracked_position(self) -> TestnetTrackedPosition | None:
        return self._testnet_position

    def testnet_set_position(self, pos: TestnetTrackedPosition) -> None:
        self._testnet_position = pos

    def testnet_clear_position(self) -> None:
        self._testnet_position = None

    def append_testnet_order(self, record: TestnetOrderRecord) -> None:
        self._testnet_orders.append(record)

    def testnet_orders_newest_first(self) -> list[TestnetOrderRecord]:
        return list(reversed(self._testnet_orders))

    def set_last_error(self, value: str | None) -> None:
        self._last_error = value

    def last_error(self) -> str | None:
        return self._last_error

    def chief_demo_autonomy_enabled(self) -> bool:
        return self._chief_demo_autonomy_enabled

    def set_chief_demo_autonomy_enabled(self, value: bool) -> None:
        self._chief_demo_autonomy_enabled = value

    def set_last_chief_decision(self, decision: dict[str, object] | None) -> None:
        self._last_chief_decision = dict(decision) if decision is not None else None

    def last_chief_decision(self) -> dict[str, object] | None:
        return dict(self._last_chief_decision) if self._last_chief_decision is not None else None

    def demo_week_enabled(self) -> bool:
        return self._demo_week_enabled

    def set_demo_week_enabled(self, value: bool) -> None:
        self._demo_week_enabled = value

    def demo_week_blocked_reason(self, *, order_usdt: float | None = None) -> str | None:
        if not self._demo_week_enabled:
            return None
        snap = self.exec_gate_snapshot()
        pnl_today = float(snap.get("realized_pnl_today") or 0.0)
        trades_today = int(snap.get("opens_today") or 0)
        if self.effective_open_positions_for_risk() >= DEMO_MAX_OPEN_POSITIONS:
            return "Demo Week Mode: max open positions reached."
        if trades_today >= DEMO_MAX_DAILY_TRADES:
            return "Demo Week Mode: max daily trades reached."
        if pnl_today <= -float(DEMO_MAX_DAILY_LOSS_USDT):
            return "Demo Week Mode: max daily loss reached."
        if order_usdt is not None and order_usdt > float(DEMO_MAX_ORDER_USDT):
            return "Demo Week Mode: order size exceeds max order USDT."
        return None

    def demo_week_status(self) -> dict[str, object]:
        snap = self.exec_gate_snapshot()
        blocked_reason = self.demo_week_blocked_reason()
        return {
            "enabled": self._demo_week_enabled,
            "daily_trades_used": int(snap.get("opens_today") or 0),
            "daily_realized_pnl": float(snap.get("realized_pnl_today") or 0.0),
            "max_daily_loss": DEMO_MAX_DAILY_LOSS_USDT,
            "max_daily_trades": DEMO_MAX_DAILY_TRADES,
            "max_order_size": DEMO_MAX_ORDER_USDT,
            "open_positions_count": self.effective_open_positions_for_risk(),
            "blocked_reason": blocked_reason,
        }

    def next_trade_id(self) -> str:
        self._trade_seq += 1
        return f"demo-{self._trade_seq}"

    def next_demo_price_tick_seq(self) -> int:
        """Monotonic counter for deterministic demo display jitter per tick."""
        self._demo_price_tick_seq += 1
        return self._demo_price_tick_seq

    def update_open_trade_prices(self, prices: dict[str, float]) -> None:
        """Mark open trades to latest demo display prices and refresh unrealized P/L."""
        for trade in self._open_trades.values():
            if not trade.is_open:
                continue
            # Spot Testnet positions track Binance Testnet ticker + fills — never overwrite
            # with ``demo_display_price_map`` (mainnet/public jitter feed); that inflated P/L
            # vs realized USDT from Testnet orders (users saw huge profit, history huge loss).
            if getattr(trade, "source", "") == TRADE_SOURCE_BINANCE_TESTNET:
                continue
            px = prices.get(trade.symbol)
            if px is None:
                continue
            trade.current_price = px
            trade.profit_loss = demo_unrealized_pnl(trade)

    def snapshot_open_trades(self) -> dict[str, DemoTrade]:
        return dict(self._open_trades)

    def open_positions_count(self) -> int:
        return len(self._open_trades)

    def add_open_trade(self, trade: DemoTrade) -> None:
        self._open_trades[trade.id] = trade

    def remove_open(self, trade_id: str) -> DemoTrade | None:
        return self._open_trades.pop(trade_id, None)

    def push_history(self, trade: DemoTrade) -> None:
        self._history.append(trade)
        if not trade.is_open:
            self.exec_gate_on_closed_trade(trade)
        if (trade.source or "") == TRADE_SOURCE_BINANCE_TESTNET and not trade.is_open:
            self.testnet_register_closed_trade(trade)

    def testnet_register_closed_trade(self, trade: DemoTrade) -> None:
        """Cooldown, loss streak, and optional halt after a Spot Testnet close."""
        sym = trade.symbol.strip().upper()
        now = self.utc_now()
        pl = float(trade.profit_loss or 0.0)
        self._testnet_symbol_cooldown_until[sym] = now + timedelta(
            minutes=TESTNET_STRATEGY_COOLDOWN_MINUTES,
        )
        if pl < 0:
            self._testnet_symbol_loss_streak[sym] = self._testnet_symbol_loss_streak.get(sym, 0) + 1
        else:
            self._testnet_symbol_loss_streak[sym] = 0
        if self._testnet_symbol_loss_streak.get(sym, 0) >= TESTNET_STRATEGY_MAX_CONSECUTIVE_LOSSES:
            self._testnet_symbol_halted_until[sym] = now + timedelta(
                hours=TESTNET_STRATEGY_HALT_HOURS,
            )

    def testnet_last_closed_trade_was_loss(self, symbol: str) -> bool:
        sym = symbol.strip().upper()
        for t in reversed(self._history):
            if t.symbol.strip().upper() != sym:
                continue
            if not t.is_open and (t.source or "") == TRADE_SOURCE_BINANCE_TESTNET:
                return float(t.profit_loss or 0.0) < 0
        return False

    def testnet_buy_blocked_reason(self, symbol: str) -> str | None:
        """None if a new BUY on ``symbol`` is allowed by cooldown/halt rules."""
        sym = symbol.strip().upper()
        now = self.utc_now()
        hu = self._testnet_symbol_halted_until.get(sym)
        if hu is not None and now < hu:
            return (
                f"Symbol {sym} halted after {TESTNET_STRATEGY_MAX_CONSECUTIVE_LOSSES} "
                f"consecutive losses until {hu.isoformat()}."
            )
        if hu is not None and now >= hu:
            self._testnet_symbol_halted_until.pop(sym, None)
            self._testnet_symbol_loss_streak[sym] = 0
        cu = self._testnet_symbol_cooldown_until.get(sym)
        if cu is not None and now < cu:
            return (
                f"Cooldown on {sym}: next BUY allowed after {cu.isoformat()} "
                f"({TESTNET_STRATEGY_COOLDOWN_MINUTES}m after last close)."
            )
        return None

    def append_decision(self, decision: DecisionModel) -> None:
        self._decisions.append(decision)

    def decisions_newest_first(self) -> list[DecisionModel]:
        return list(reversed(self._decisions))

    def decisions_count(self) -> int:
        return len(self._decisions)

    def set_latest_agents(self, agents: list[AgentResultModel]) -> None:
        self._latest_agents = list(agents)

    def latest_agents(self) -> list[AgentResultModel]:
        return list(self._latest_agents)

    def append_lesson(self, lesson: LessonModel) -> None:
        self._lessons.append(lesson)

    def lessons_newest_first(self) -> list[LessonModel]:
        return list(reversed(self._lessons))

    def lessons_count(self) -> int:
        return len(self._lessons)

    def set_last_cycle(self, payload: BotCycleResultModel | None) -> None:
        self._last_cycle = payload

    def last_cycle(self) -> BotCycleResultModel | None:
        return self._last_cycle

    def history_trades(self) -> list[DemoTrade]:
        return list(self._history)

    def history_count(self) -> int:
        return len(self._history)

    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def set_last_open_skipped_reason(self, value: str | None) -> None:
        self._last_open_skipped_reason = value

    def last_open_skipped_reason(self) -> str | None:
        return self._last_open_skipped_reason

    def exec_gate_ensure_day(self) -> None:
        today = self.utc_now().date()
        if self._exec_gate_day != today:
            self._exec_gate_day = today
            self._exec_gate_realized_pnl_today = 0.0
            self._exec_gate_opens_today = 0

    def exec_gate_on_closed_trade(self, trade: DemoTrade) -> None:
        """Roll realized P/L into today's execution-gate bucket (scoped to mode)."""
        want = want_source_for_execution_mode(self._execution_mode)
        if not trade_matches_execution_source(trade, want):
            return
        self.exec_gate_ensure_day()
        self._exec_gate_realized_pnl_today += float(trade.profit_loss or 0.0)

    def exec_gate_on_successful_open(self) -> None:
        self.exec_gate_ensure_day()
        self._exec_gate_opens_today += 1
        self._exec_gate_last_open_utc = self.utc_now()

    def exec_gate_snapshot(self) -> dict[str, object]:
        self.exec_gate_ensure_day()
        return {
            "utc_day": self._exec_gate_day.isoformat() if self._exec_gate_day else None,
            "realized_pnl_today": self._exec_gate_realized_pnl_today,
            "opens_today": self._exec_gate_opens_today,
            "last_open_utc": (
                self._exec_gate_last_open_utc.isoformat()
                if self._exec_gate_last_open_utc
                else None
            ),
        }

    def consecutive_closed_losses(self, symbol: str) -> int:
        """Loss streak for closed trades in the current execution mode (most recent first)."""
        sym = symbol.strip().upper()
        want = want_source_for_execution_mode(self._execution_mode)
        streak = 0
        for t in reversed(self._history):
            if t.is_open:
                continue
            if not trade_matches_execution_source(t, want):
                continue
            if t.symbol.strip().upper() != sym:
                continue
            if float(t.profit_loss or 0.0) < 0:
                streak += 1
            else:
                break
        return streak

    def drawdown_proxy(self) -> float:
        """
        Simple stress read: negative total realized P/L in scope (all history for mode),
        not intraday max DD.
        """
        want = want_source_for_execution_mode(self._execution_mode)
        total = 0.0
        for t in self._history:
            if t.is_open:
                continue
            if not trade_matches_execution_source(t, want):
                continue
            total += float(t.profit_loss or 0.0)
        return min(0.0, total)

    def reset_demo_state(self) -> None:
        """Development-only reset for volatile demo state; does not touch settings or keys."""
        self._started = False
        self._open_trades.clear()
        self._history.clear()
        self._decisions.clear()
        self._latest_agents.clear()
        self._lessons.clear()
        self._last_cycle = None
        self._trade_seq = 0
        self._last_open_skipped_reason = None
        self._demo_price_tick_seq = 0
        self._testnet_orders.clear()
        self._testnet_position = None
        self._testnet_symbol_cooldown_until.clear()
        self._testnet_symbol_loss_streak.clear()
        self._testnet_symbol_halted_until.clear()
        self._exec_gate_day = self.utc_now().date()
        self._exec_gate_realized_pnl_today = 0.0
        self._exec_gate_opens_today = 0
        self._exec_gate_last_open_utc = None
        self._last_chief_decision = None
        self._last_error = None
