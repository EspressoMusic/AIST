from fastapi import APIRouter, Depends

from app.deps import get_binance_testnet_service, get_bot_state_service
from app.demo_bot_constants import TRADE_SOURCE_BINANCE_TESTNET
from app.models.demo_trade import DemoTrade, demo_unrealized_pnl
from app.models.trade_model import TradeDetailResponse, TradesBundleResponse
from app.services.binance_testnet_service import BinanceTestnetService
from app.services.bot_state_service import BotStateService
from app.services.testnet_open_mtm import refresh_binance_testnet_open_trade_mtm
from app.trade_scope import trade_matches_execution_source, want_source_for_execution_mode

router = APIRouter(tags=["trades"])


def _to_detail(trade: DemoTrade) -> TradeDetailResponse:
    exit_px = trade.exit_price if trade.exit_price is not None else None
    if not trade.is_open and exit_px is None:
        exit_px = trade.current_price
    # Align with GET /portfolio: closed = stored profit_loss; open = MTM (Testnet live via refresh).
    if trade.is_open:
        pl_out = float(demo_unrealized_pnl(trade))
    else:
        pl_out = float(trade.profit_loss or 0.0)
    return TradeDetailResponse(
        id=trade.id,
        symbol=trade.symbol,
        side=trade.side.upper(),
        status="OPEN" if trade.is_open else "CLOSED",
        entry_price=trade.entry_price,
        current_price=trade.current_price,
        profit_loss=pl_out,
        quantity=float(trade.quantity or 0.0),
        opened_at=trade.opened_at,
        closed_at=trade.closed_at,
        exit_price=exit_px,
        reason=trade.reason or "",
        source=trade.source or "PAPER_DEMO",
        binance_order_id=trade.binance_order_id,
        buy_order_id=trade.binance_order_id,
        sell_order_id=trade.sell_order_id,
        buy_cummulative_quote_qty=trade.buy_quote_cost,
        sell_cummulative_quote_qty=trade.sell_quote_proceeds,
    )


@router.get("/trades", response_model=TradesBundleResponse)
def list_trades(
    state: BotStateService = Depends(get_bot_state_service),
    binance: BinanceTestnetService = Depends(get_binance_testnet_service),
) -> TradesBundleResponse:
    want = want_source_for_execution_mode(state.execution_mode)
    open_trades = sorted(
        [t for t in state.snapshot_open_trades().values() if trade_matches_execution_source(t, want)],
        key=lambda t: t.opened_at,
        reverse=True,
    )
    for t in open_trades:
        if (t.source or "") == TRADE_SOURCE_BINANCE_TESTNET:
            refresh_binance_testnet_open_trade_mtm(t, binance)
    history = sorted(
        [t for t in state.history_trades() if trade_matches_execution_source(t, want)],
        key=lambda t: t.closed_at or t.opened_at,
        reverse=True,
    )
    return TradesBundleResponse(
        open_trades=[_to_detail(t) for t in open_trades],
        history=[_to_detail(t) for t in history],
    )
