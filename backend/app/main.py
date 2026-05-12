from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings, parse_csv
from app.deps import get_paper_autonomy_service
from app.routes import (
    ai_advisor_routes,
    ai_team_routes,
    alpaca_paper_routes,
    binance_testnet_routes,
    bot_insights_routes,
    bot_routes,
    chief_bot_routes,
    demo_week_routes,
    dev_routes,
    health_routes,
    market_routes,
    market_intel_routes,
    performance_routes,
    portfolio_routes,
    trade_routes,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    cors_origins = parse_csv(settings.cors_origins)
    allow_all_origins = "*" in cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all_origins else cors_origins,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=not allow_all_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_routes.router)
    app.include_router(ai_advisor_routes.router)
    app.include_router(ai_team_routes.router)
    app.include_router(alpaca_paper_routes.router)
    app.include_router(binance_testnet_routes.router)
    app.include_router(market_routes.router)
    app.include_router(market_intel_routes.router)
    app.include_router(portfolio_routes.router)
    app.include_router(performance_routes.router)
    app.include_router(trade_routes.router)
    app.include_router(bot_routes.router)
    app.include_router(bot_insights_routes.router)
    app.include_router(chief_bot_routes.router)
    app.include_router(demo_week_routes.router)
    app.include_router(dev_routes.router)

    @app.on_event("startup")
    async def _start_paper_autonomy_loop() -> None:
        get_paper_autonomy_service().start_background_loop()

    @app.on_event("shutdown")
    async def _stop_paper_autonomy_loop() -> None:
        await get_paper_autonomy_service().stop_background_loop()

    return app


app = create_app()
