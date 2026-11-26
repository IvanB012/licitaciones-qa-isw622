"""Rutas de UI (HTML). Cada módulo registra su router aquí:

    from app.web import tenders
    web_router.include_router(tenders.router)

Toda ruta de UI protegida debe declarar ``Depends(require_user)`` (o require_admin):
sin sesión el handler de errores redirige a /login.
"""
from fastapi import APIRouter

from app.web import exchange_rates, offers, pages, providers, tenders

web_router = APIRouter()
web_router.include_router(pages.router)
web_router.include_router(exchange_rates.router)
web_router.include_router(providers.router)
web_router.include_router(tenders.router)
web_router.include_router(offers.router)
