from typing import Any

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import (
    get_ai_provider_service,
    get_alpaca_paper_service,
    get_alpaca_news_service,
    get_analyst_data_service,
    get_binance_testnet_service,
    get_bot_state_service,
)
from app.services.alpaca_news_service import AlpacaNewsService
from app.services.alpaca_paper_service import AlpacaPaperService
from app.services.analyst_data_service import AnalystDataService
from app.services.ai_provider_service import AIProviderService
from app.services.binance_testnet_service import BinanceTestnetService
from app.services.bot_state_service import BotStateService

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {
        "status": "ok",
        "backend_ok": True,
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/system/health")
def system_health(
    state: BotStateService = Depends(get_bot_state_service),
    settings: Settings = Depends(get_settings),
    ai: AIProviderService = Depends(get_ai_provider_service),
    binance: BinanceTestnetService = Depends(get_binance_testnet_service),
    alpaca: AlpacaPaperService = Depends(get_alpaca_paper_service),
    alpaca_news: AlpacaNewsService = Depends(get_alpaca_news_service),
    analyst: AnalystDataService = Depends(get_analyst_data_service),
) -> dict[str, Any]:
    binance_ok = False
    last_error = state.last_error()
    if settings.use_binance_testnet and binance.is_configured:
        try:
            binance.ping()
            binance_ok = True
        except Exception as exc:
            last_error = str(exc)
            state.set_last_error(last_error)
    alpaca_status = alpaca.get_status()
    alpaca_ok = False
    if alpaca_status.get("configured") and alpaca_status.get("paper_endpoint_ok"):
        try:
            alpaca.get_account()
            alpaca_ok = True
        except Exception as exc:
            last_error = str(exc)
            state.set_last_error(last_error)
    news_status = alpaca_news.get_status()
    analyst_status = analyst.get_status()
    return {
        "backend_ok": True,
        "execution_mode": state.execution_mode.value,
        "ai_provider": ai.status().get("active_provider", "MOCK"),
        "binance_testnet_ok": binance_ok,
        "alpaca_paper_ok": alpaca_ok,
        "alpaca_paper_status": alpaca_status,
        "news_provider_status": news_status
        if settings.news_provider.strip().upper() == "ALPACA_NEWS"
        else {
            "provider": settings.news_provider,
            "configured": bool(
                settings.news_provider == "MOCK"
                or settings.cryptopanic_api_key
                or settings.finnhub_api_key
                or settings.newsapi_api_key
                or settings.news_rss_urls
            ),
            "ok": settings.news_provider == "MOCK",
            "message": "Legacy news provider status.",
        },
        "analyst_provider_status": analyst_status,
        "agents_ready": True,
        "chief_manager_ready": True,
        "demo_week_enabled": state.demo_week_enabled(),
        "kill_switch_active": bool(settings.bot_kill_switch),
        "last_error": last_error,
    }
