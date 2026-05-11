"""Shared service singletons for FastAPI dependencies."""

from __future__ import annotations

from app.config import get_settings
from app.agents.ai_team.ai_team_service import AiTeamService
from app.services.bot_engine_service import BotEngineService
from app.services.bot_state_service import BotStateService
from app.services.binance_testnet_service import BinanceTestnetService
from app.services.alpaca_paper_service import AlpacaPaperService
from app.services.ai_provider_service import AIProviderService
from app.services.exchange_service import ExchangeService
from app.services.news_source_service import NewsSourceService
from app.services.news_data_service import NewsDataService
from app.services.portfolio_service import PortfolioService

# Single shared bot state (trades, decisions, etc.)
_bot_state_service = BotStateService()

# Portfolio reads from the same BotStateService as the bot engine
_binance_testnet_service = BinanceTestnetService(get_settings())
_alpaca_paper_service = AlpacaPaperService(get_settings())
_portfolio_service = PortfolioService(
    _bot_state_service,
    _binance_testnet_service,
)

_exchange_service = ExchangeService()
_ai_provider_service = AIProviderService(get_settings())
_news_source_service = NewsSourceService(get_settings())
_news_data_service = NewsDataService(_news_source_service)
_ai_team_service = AiTeamService(
    exchange=_exchange_service,
    state=_bot_state_service,
    settings=get_settings(),
    news_data=_news_data_service,
    ai_provider=_ai_provider_service,
    alpaca_paper=_alpaca_paper_service,
)
_bot_engine_service = BotEngineService(
    exchange=_exchange_service,
    state=_bot_state_service,
    binance_testnet=_binance_testnet_service,
    alpaca_paper=_alpaca_paper_service,
    settings=get_settings(),
    ai_provider=_ai_provider_service,
    news_source=_news_source_service,
)
_ai_team_service.set_execution_bridge(_bot_engine_service)


def get_exchange_service() -> ExchangeService:
    return _exchange_service


def get_binance_testnet_service() -> BinanceTestnetService:
    """Spot Testnet REST + signing (same settings as public ticker helper)."""
    return _binance_testnet_service


def get_alpaca_paper_service() -> AlpacaPaperService:
    """Alpaca Paper REST client. Never live trading."""
    return _alpaca_paper_service


def get_ai_provider_service() -> AIProviderService:
    return _ai_provider_service


def get_news_source_service() -> NewsSourceService:
    return _news_source_service


def get_news_data_service() -> NewsDataService:
    return _news_data_service


def get_ai_team_service() -> AiTeamService:
    return _ai_team_service


def get_bot_state_service() -> BotStateService:
    return _bot_state_service


def get_bot_engine_service() -> BotEngineService:
    return _bot_engine_service


def get_portfolio_service() -> PortfolioService:
    """FastAPI Depends target — must import successfully from app.deps."""
    return _portfolio_service
