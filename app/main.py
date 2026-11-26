"""Fábrica de la aplicación.

    uvicorn app.main:app --reload          (usa get_settings(); `app` se crea al primer acceso)

Pruebas: create_app(settings=..., engine=..., clock=FakeClock(), rate_provider=FailingExchangeRateProvider())
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from starlette.middleware.sessions import SessionMiddleware

from app.api import api_router
from app.clock import Clock, SystemClock
from app.config import Settings, get_settings
from app.db import create_tables, make_engine, make_session_factory
from app.errors import register_error_handlers
from app.exchange import ExchangeRateProvider, FailingExchangeRateProvider, HttpExchangeRateProvider
from app.web import web_router

STATIC_DIR = Path(__file__).parent / "static"
SESSION_MAX_AGE = 8 * 60 * 60  # 8 horas


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    clock: Clock | None = None,
    rate_provider: ExchangeRateProvider | None = None,
) -> FastAPI:
    """Crea la app. Todo lo inyectable tiene un valor por defecto seguro:
    BD de settings.database_url, SystemClock y proveedor de tipo de cambio HTTP (ENV=test: uno que falla, sin red).
    """
    settings = settings or get_settings()
    engine = engine or make_engine(settings.database_url)
    create_tables(engine)

    app = FastAPI(
        title="Sistema de Gestión de Licitaciones",
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.clock = clock or SystemClock()
    if rate_provider is None:  # app real: proveedor HTTP; ENV=test: siempre el que falla (sin red)
        rate_provider = (
            FailingExchangeRateProvider()
            if settings.env.lower() == "test"
            else HttpExchangeRateProvider(settings.exchange_rate_url)
        )
    app.state.rate_provider = rate_provider

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="session",
        max_age=SESSION_MAX_AGE,
        same_site="lax",
        https_only=settings.is_prod,
    )
    register_error_handlers(app)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(api_router)
    app.include_router(web_router)
    return app


def __getattr__(name: str):
    # `app` perezoso: importar app.main (p. ej. en tests) no crea ninguna BD.
    if name == "app":
        instance = create_app()
        globals()["app"] = instance
        return instance
    raise AttributeError(name)
