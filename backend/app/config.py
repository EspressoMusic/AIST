"""Application settings. Loads optional .env — no real keys required for demo."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Trading Bot API"
    debug: bool = False
    environment: str = "development"
    execution_mode: str = "BINANCE_TESTNET"

    # Server startup. Used by `python -m app.run`; cloud platforms may also set
    # PORT and run uvicorn directly.
    host: str = "0.0.0.0"
    port: int = 8001

    # Binance Spot Testnet (keys only in backend/.env — never in Flutter)
    binance_testnet_api_key: str = ""
    binance_testnet_api_secret: str = ""
    binance_testnet_base_url: str = "https://testnet.binance.vision/api"
    use_binance_testnet: bool = False

    # Alpaca Paper Trading (server-side paper credentials only; never live endpoint).
    alpaca_paper_api_key: str = ""
    alpaca_paper_api_secret: str = ""
    alpaca_paper_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_base_url: str = "https://data.alpaca.markets"

    # Public spot REST (read-only ticker prices — no API key)
    binance_public_base_url: str = "https://api.binance.com"

    # When true, bot refuses new opens (SELL / closes still allowed where applicable).
    bot_kill_switch: bool = False

    # AI advisor layer (recommendations only; execution gates remain authoritative).
    ai_advisor_provider: str = "MOCK"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-1.5-flash"
    ai_advisor_timeout_seconds: float = 60.0

    # News source for News Agent. Choose: MOCK, CRYPTOPANIC, FINNHUB, NEWSAPI, RSS.
    news_provider: str = "MOCK"
    cryptopanic_api_key: str = ""
    finnhub_api_key: str = ""
    newsapi_api_key: str = ""
    news_lookback_hours: int = 12
    news_max_items: int = 12
    # Comma-separated RSS feed URLs, e.g. CoinDesk/Cointelegraph feeds.
    news_rss_urls: str = ""

    # CORS — comma-separated origins for Flutter web/cloud access.
    # Use "*" for public demo testing; set exact HTTPS origins in production.
    cors_origins: str = "*"
    cors_origin_regex: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
