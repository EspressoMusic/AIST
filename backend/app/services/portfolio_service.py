"""Demo portfolio derived from in-memory bot trades (paper + Binance Testnet)."""

from __future__ import annotations

import logging

from app.demo_bot_constants import TRADE_SOURCE_BINANCE_TESTNET
from app.models.demo_trade import demo_unrealized_pnl
from app.models.portfolio_model import PortfolioResponse
from app.services.binance_testnet_service import BinanceTestnetService
from app.services.bot_state_service import BotStateService
from app.services.testnet_open_mtm import refresh_binance_testnet_open_trade_mtm
from app.trade_scope import trade_matches_execution_source, want_source_for_execution_mode

_STARTING_BALANCE = 10000.0

logger = logging.getLogger(__name__)


class PortfolioService:
    def __init__(
        self,
        state: BotStateService,
        binance_testnet: BinanceTestnetService,
    ) -> None:
        self._state = state
        self._binance = binance_testnet

    def get_portfolio(self) -> PortfolioResponse:
        mode = self._state.execution_mode
        want_source = want_source_for_execution_mode(mode)

        open_all = list(self._state.snapshot_open_trades().values())
        history_all = self._state.history_trades()

        open_trades = [t for t in open_all if trade_matches_execution_source(t, want_source)]
        history = [t for t in history_all if trade_matches_execution_source(t, want_source)]

        realized_profit_loss = 0.0
        for t in history:
            pl_hist = float(t.profit_loss or 0.0)
            realized_profit_loss += pl_hist
            logger.info(
                "GET /portfolio history id=%s source=%s profit_loss=%.8f "
                "buy_quote=%s sell_quote=%s exit_price=%s entry_price=%.8f qty=%.8f",
                t.id,
                getattr(t, "source", ""),
                pl_hist,
                t.buy_quote_cost,
                t.sell_quote_proceeds,
                t.exit_price,
                t.entry_price,
                t.quantity,
            )

        unrealized_profit_loss = 0.0
        for t in open_trades:
            if (t.source or "") == TRADE_SOURCE_BINANCE_TESTNET:
                refresh_binance_testnet_open_trade_mtm(t, self._binance)
            else:
                t.profit_loss = float(demo_unrealized_pnl(t))
            pl = float(t.profit_loss or 0.0)
            unrealized_profit_loss += pl

        total_profit_loss = realized_profit_loss + unrealized_profit_loss
        current_value = _STARTING_BALANCE + total_profit_loss
        expected_cv = _STARTING_BALANCE + realized_profit_loss + unrealized_profit_loss
        if abs(current_value - expected_cv) > 1e-6:
            logger.error(
                "Portfolio invariant broken: current_value=%s expected=%s",
                current_value,
                expected_cv,
            )

        change_percent = (
            (total_profit_loss / _STARTING_BALANCE) * 100.0
            if _STARTING_BALANCE
            else 0.0
        )

        logger.info(
            "GET /portfolio mode=%s want_source=%s open_trades_count=%s closed_trades_count=%s "
            "realized_profit_loss=%.8f unrealized_profit_loss=%.8f total_profit_loss=%.8f "
            "current_value=%.8f starting_balance=%.8f",
            mode.value,
            want_source,
            len(open_trades),
            len(history),
            realized_profit_loss,
            unrealized_profit_loss,
            total_profit_loss,
            current_value,
            _STARTING_BALANCE,
        )
        for t in open_trades:
            logger.info(
                "GET /portfolio open trade id=%s source=%s side=%s "
                "profit_loss=%.8f entry_price=%.8f current_price=%.8f quantity=%.8f",
                t.id,
                getattr(t, "source", ""),
                t.side,
                t.profit_loss,
                t.entry_price,
                t.current_price,
                t.quantity,
            )
        return PortfolioResponse(
            starting_balance=_STARTING_BALANCE,
            current_value=current_value,
            total_profit_loss=total_profit_loss,
            change_percent=change_percent,
            realized_profit_loss=realized_profit_loss,
            unrealized_profit_loss=unrealized_profit_loss,
            open_trades_count=len(open_trades),
            closed_trades_count=len(history),
        )
