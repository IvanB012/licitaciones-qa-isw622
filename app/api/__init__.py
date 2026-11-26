"""Routers de la API (prefijo /api). Cada módulo registra su router aquí:

    from app.api import tenders
    api_router.include_router(tenders.router)
"""
from fastapi import APIRouter

from app.api import auth, health, offers, tenders

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tenders.router)
api_router.include_router(offers.router)
