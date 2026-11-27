"""Routers de la API (prefijo /api). Cada módulo registra su router aquí:

    from app.api import tenders
    api_router.include_router(tenders.router)
"""
from fastapi import APIRouter

from app.api import approval_ranges, auth, evaluation, exchange_rates, health, offers, providers, tenders, users

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(approval_ranges.router)
api_router.include_router(exchange_rates.router)
api_router.include_router(providers.router)
api_router.include_router(tenders.router)
api_router.include_router(offers.router)
api_router.include_router(evaluation.router)
api_router.include_router(users.router)
