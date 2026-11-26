"""Proveedor externo de tipo de cambio (contrato §11). Solo la interfaz y dobles de prueba.

La implementación HTTP real (httpx) la aporta otra rama. Las pruebas NUNCA tocan la red.
"""
from decimal import Decimal
from typing import Protocol

from fastapi import Request


class ExchangeRateUnavailable(Exception):
    """El servicio externo falló o no respondió."""


class ExchangeRateProvider(Protocol):
    def get_rate(self) -> Decimal:
        """CRC por 1 USD. Lanza ExchangeRateUnavailable si el servicio falla."""
        ...


class FailingExchangeRateProvider:
    """Simula un servicio caído (respuesta HTTP 500). Es el proveedor por defecto y el de las pruebas."""

    def get_rate(self) -> Decimal:
        raise ExchangeRateUnavailable("Servicio de tipo de cambio no disponible (simulado: HTTP 500)")


class FakeExchangeRateProvider:
    """Devuelve una tasa fija (por defecto 500.00 CRC por USD) sin red. Para probar el camino feliz de 'Sugerir tasa'."""

    def __init__(self, rate: Decimal | str = "500.00") -> None:
        self._rate = Decimal(str(rate))

    def get_rate(self) -> Decimal:
        return self._rate


def get_rate_provider(request: Request) -> ExchangeRateProvider:
    """Dependencia FastAPI. Se inyecta en create_app(rate_provider=...) o con app.dependency_overrides."""
    return request.app.state.rate_provider
