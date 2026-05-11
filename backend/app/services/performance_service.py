"""Closed-trade performance stats scoped like GET /trades history."""

from __future__ import annotations

from collections import defaultdict

from app.models.demo_trade import DemoTrade
from app.models.performance_model import (
    PerformanceResponse,
    PerformanceTradeBrief,
    SymbolPerformanceSummary,
)
from app.services.bot_state_service import BotStateService
from app.trade_scope import trade_matches_execution_source, want_source_for_execution_mode


def _closed_pl(trade: DemoTrade) -> float:
    return float(trade.profit_loss or 0.0)


def build_performance_response(state: BotStateService) -> PerformanceResponse:
    mode = state.execution_mode
    want = want_source_for_execution_mode(mode)

    closed: list[DemoTrade] = [
        t
        for t in state.history_trades()
        if (not t.is_open) and trade_matches_execution_source(t, want)
    ]

    n = len(closed)
    if n == 0:
        return PerformanceResponse(
            execution_mode=mode.value,  # type: ignore[arg-type]
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            break_even_trades=0,
            win_rate=0.0,
            total_realized_profit_loss=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            average_profit=None,
            average_loss=None,
            average_trade_profit_loss=None,
            best_trade=None,
            worst_trade=None,
            profit_factor=None,
            symbols=[],
            recommendation_summary="No closed trades yet. Run demo cycles before reviewing performance.",
        )

    winning = losing = be = 0
    total_pl = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    sum_win = 0.0
    sum_loss = 0.0

    best: DemoTrade | None = None
    worst: DemoTrade | None = None
    best_pl: float | None = None
    worst_pl: float | None = None

    by_sym: dict[str, list[DemoTrade]] = defaultdict(list)
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    current_loss_streak = 0
    longest_loss_streak = 0
    hold_seconds: list[float] = []

    for t in closed:
        pl = _closed_pl(t)
        by_sym[t.symbol.strip().upper()].append(t)
        total_pl += pl
        equity += pl
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
        if t.opened_at is not None and t.closed_at is not None:
            hold_seconds.append(max(0.0, (t.closed_at - t.opened_at).total_seconds()))
        if pl > 0:
            winning += 1
            gross_profit += pl
            sum_win += pl
            current_loss_streak = 0
        elif pl < 0:
            losing += 1
            gross_loss += pl
            sum_loss += pl
            current_loss_streak += 1
            longest_loss_streak = max(longest_loss_streak, current_loss_streak)
        else:
            be += 1

        if best is None or (best_pl is not None and pl > best_pl):
            best = t
            best_pl = pl
        if worst is None or (worst_pl is not None and pl < worst_pl):
            worst = t
            worst_pl = pl

    win_rate = (winning / n) * 100.0 if n else 0.0
    avg_trade = total_pl / n if n else None
    avg_profit = (sum_win / winning) if winning else None
    avg_loss = (sum_loss / losing) if losing else None

    pf: float | None
    if gross_loss == 0.0:
        pf = None
    else:
        pf = gross_profit / abs(gross_loss)

    symbols_out: list[SymbolPerformanceSummary] = []
    symbol_totals: dict[str, float] = {}
    for sym in sorted(by_sym.keys()):
        rows = by_sym[sym]
        w = l = b = 0
        t_pl = gp = gl = 0.0
        for tr in rows:
            p = _closed_pl(tr)
            t_pl += p
            if p > 0:
                w += 1
                gp += p
            elif p < 0:
                l += 1
                gl += p
            else:
                b += 1
        symbol_totals[sym] = t_pl
        symbols_out.append(
            SymbolPerformanceSummary(
                symbol=sym,
                total_trades=len(rows),
                winning_trades=w,
                losing_trades=l,
                break_even_trades=b,
                total_realized_profit_loss=t_pl,
                gross_profit=gp,
                gross_loss=gl,
            ),
        )

    best_symbol = max(symbol_totals, key=symbol_totals.get) if symbol_totals else None
    worst_symbol = min(symbol_totals, key=symbol_totals.get) if symbol_totals else None
    recent = sorted(closed, key=lambda t: t.closed_at or t.opened_at, reverse=True)[:10]
    last_10 = [
        {
            "id": t.id,
            "symbol": t.symbol,
            "profit_loss": _closed_pl(t),
            "closed_at": t.closed_at,
            "source": t.source,
        }
        for t in recent
    ]
    recommendation = "Performance is neutral; keep collecting demo data."
    if n >= 3 and win_rate >= 55 and total_pl > 0:
        recommendation = "Demo performance is positive; continue testing with current risk caps."
    elif n >= 3 and (win_rate < 40 or total_pl < 0):
        recommendation = "Demo performance is weak; reduce size or pause new entries for review."

    def _brief(tr: DemoTrade) -> PerformanceTradeBrief:
        return PerformanceTradeBrief(
            id=tr.id,
            symbol=tr.symbol,
            profit_loss=_closed_pl(tr),
            closed_at=tr.closed_at,
        )

    return PerformanceResponse(
        execution_mode=mode.value,  # type: ignore[arg-type]
        total_trades=n,
        winning_trades=winning,
        losing_trades=losing,
        break_even_trades=be,
        win_rate=win_rate,
        total_realized_profit_loss=total_pl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        average_profit=avg_profit,
        average_loss=avg_loss,
        average_trade_profit_loss=avg_trade,
        best_trade=_brief(best) if best is not None else None,
        worst_trade=_brief(worst) if worst is not None else None,
        profit_factor=pf,
        symbols=symbols_out,
        max_drawdown=max_drawdown,
        consecutive_losses=longest_loss_streak,
        current_loss_streak=current_loss_streak,
        best_symbol=best_symbol,
        worst_symbol=worst_symbol,
        average_hold_time=(sum(hold_seconds) / len(hold_seconds)) if hold_seconds else None,
        last_10_trades_summary=last_10,
        recommendation_summary=recommendation,
    )
