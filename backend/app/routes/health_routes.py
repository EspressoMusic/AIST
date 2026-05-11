from typing import Any

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import (
    get_ai_provider_service,
    get_binance_testnet_service,
    get_bot_state_service,
)
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
    return {
        "backend_ok": True,
        "execution_mode": state.execution_mode.value,
        "ai_provider": ai.status().get("active_provider", "MOCK"),
        "binance_testnet_ok": binance_ok,
        "news_provider_status": {
            "provider": settings.news_provider,
            "configured": bool(
                settings.news_provider == "MOCK"
                or settings.cryptopanic_api_key
                or settings.finnhub_api_key
                or settings.newsapi_api_key
                or settings.news_rss_urls
            ),
        },
        "agents_ready": True,
        "chief_manager_ready": True,
        "demo_week_enabled": state.demo_week_enabled(),
        "kill_switch_active": bool(settings.bot_kill_switch),
        "last_error": last_error,
    }
