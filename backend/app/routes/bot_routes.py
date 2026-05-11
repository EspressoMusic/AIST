from fastapi import APIRouter, Body, Depends, HTTPException

from app.config import Settings, get_settings
from app.deps import (
    get_binance_testnet_service,
    get_bot_engine_service,
    get_bot_state_service,
)
from app.models.bot_api_model import (
    BotStartResponse,
    BotStatusResponse,
    BotStopResponse,
    BotTickOkResponse,
    BotTickStoppedResponse,
    ExecutionModeResponse,
    ExecutionModeSetRequest,
    ForceCloseResponse,
    ForceDemoTradeRequest,
    ForceDemoTradeResponse,
    TestnetOrdersResponse,
    TestnetTrackedOrderRow,
)
from app.models.execution_mode import ExecutionMode
from app.services.binance_testnet_service import BinanceTestnetService
from app.services.bot_engine_service import BotEngineService
from app.services.bot_state_service import BotStateService

router = APIRouter(prefix="/bot", tags=["bot"])


def _status_open_position_snapshot(state: BotStateService) -> dict[str, object]:
    opens = list(state.snapshot_open_trades().values())
    if not opens:
        return {
            "has_open_position": False,
            "open_position_symbol": None,
            "open_position_source": None,
            "open_position_pnl": None,
            "open_position_pnl_percent": None,
            "open_position_cycles": None,
        }
    trade = opens[0]
    if len(opens) > 1:
        for cand in opens:
            if cand.source == "BINANCE_TESTNET":
                trade = cand
                break
    entry = float(trade.entry_price)
    cur = float(trade.current_price)
    pnl = float(trade.profit_loss)
    if entry > 0 and str(trade.side).lower() == "buy":
        pct = (cur - entry) / entry * 100.0
    elif entry > 0:
        pct = (entry - cur) / entry * 100.0
    else:
        pct = None
    return {
        "has_open_position": True,
        "open_position_symbol": trade.symbol,
        "open_position_source": trade.source,
        "open_position_pnl": pnl,
        "open_position_pnl_percent": pct,
        "open_position_cycles": trade.demo_cycles_open,
    }


_TESTNET_MODE_HINT = (
    "Enable USE_BINANCE_TESTNET=true and set BINANCE_TESTNET_API_KEY / "
    "BINANCE_TESTNET_API_SECRET in backend/.env."
)


@router.get("/execution-mode", response_model=ExecutionModeResponse)
def get_execution_mode(
    state: BotStateService = Depends(get_bot_state_service),
) -> ExecutionModeResponse:
    return ExecutionModeResponse(mode=state.execution_mode.value)  # type: ignore[arg-type]


@router.post("/execution-mode", response_model=ExecutionModeResponse)
def set_execution_mode(
    body: ExecutionModeSetRequest,
    state: BotStateService = Depends(get_bot_state_service),
    settings: Settings = Depends(get_settings),
    binance: BinanceTestnetService = Depends(get_binance_testnet_service),
) -> ExecutionModeResponse:
    mode = ExecutionMode(body.mode)
    if mode == ExecutionMode.BINANCE_TESTNET:
        if not settings.use_binance_testnet:
            raise HTTPException(
                status_code=400,
                detail=(
                    "BINANCE_TESTNET mode requires USE_BINANCE_TESTNET=true "
                    f"in backend/.env. {_TESTNET_MODE_HINT}"
                ),
            )
        if not binance.is_configured:
            raise HTTPException(
                status_code=400,
                detail=f"Missing Binance testnet API credentials. {_TESTNET_MODE_HINT}",
            )
    state.set_execution_mode(mode)
    return ExecutionModeResponse(mode=mode.value)  # type: ignore[arg-type]


@router.get("/testnet-orders", response_model=TestnetOrdersResponse)
def list_bot_testnet_orders(
    state: BotStateService = Depends(get_bot_state_service),
) -> TestnetOrdersResponse:
    rows = [
        TestnetTrackedOrderRow(
            symbol=r.symbol,
            side=r.side,
            order_id=r.order_id,
            status=r.status,
            executed_qty=r.executed_qty,
            cumulative_quote_qty=r.cumulative_quote_qty,
            avg_price=r.avg_price,
            created_at=r.created_at,
            client_tag=r.client_tag,
            error_message=r.error_message,
        )
        for r in state.testnet_orders_newest_first()
    ]
    return TestnetOrdersResponse(orders=rows)


@router.post("/start", response_model=BotStartResponse)
def start_bot(
    state: BotStateService = Depends(get_bot_state_service),
    engine: BotEngineService = Depends(get_bot_engine_service),
) -> BotStartResponse:
    state.set_started(True)
    engine.run_one_cycle()
    return BotStartResponse()


@router.post("/stop", response_model=BotStopResponse)
def stop_bot(
    state: BotStateService = Depends(get_bot_state_service),
) -> BotStopResponse:
    state.set_started(False)
    return BotStopResponse()


@router.post("/force-demo-trade", response_model=ForceDemoTradeResponse)
def force_demo_trade_endpoint(
    engine: BotEngineService = Depends(get_bot_engine_service),
    body: ForceDemoTradeRequest | None = Body(default=None),
) -> ForceDemoTradeResponse:
    sym = body.symbol if body else None
    return engine.force_demo_trade(sym)


@router.post("/force-close", response_model=ForceCloseResponse)
def force_close_position(
    engine: BotEngineService = Depends(get_bot_engine_service),
) -> ForceCloseResponse:
    try:
        return engine.force_close_open_position()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/tick",
    response_model=BotTickOkResponse | BotTickStoppedResponse,
)
def tick_bot(
    state: BotStateService = Depends(get_bot_state_service),
    engine: BotEngineService = Depends(get_bot_engine_service),
) -> BotTickOkResponse | BotTickStoppedResponse:
    if not state.started:
        return BotTickStoppedResponse(
            message="Bot is stopped. POST /bot/start before ticking.",
        )
    cycle = engine.run_one_cycle()
    return BotTickOkResponse(cycle=cycle)


@router.get("/status", response_model=BotStatusResponse)
def bot_status(
    state: BotStateService = Depends(get_bot_state_service),
) -> BotStatusResponse:
    label = "started" if state.started else "stopped"
    snap = _status_open_position_snapshot(state)
    return BotStatusResponse(
        status=label,
        open_trades_count=state.open_positions_count(),
        history_count=state.history_count(),
        decisions_count=state.decisions_count(),
        execution_mode=state.execution_mode.value,  # type: ignore[arg-type]
        last_open_skipped_reason=state.last_open_skipped_reason(),
        **snap,
    )
