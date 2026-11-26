"""Proveedor externo de tipo de cambio (contrato §11): interfaz, implementación HTTP real y dobles de prueba.

Las pruebas NUNCA tocan la red: usan Failing/Fake (HttpExchangeRateProvider solo se crea en la app real).
"""
from decimal import Decimal, InvalidOperation
from typing import Protocol

import httpx
from fastapi import Request

DEFAULT_EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/USD"
HTTP_TIMEOUT_SECONDS = 3.0


class ExchangeRateUnavailable(Exception):
    """El servicio externo falló o no respondió."""


class ExchangeRateProvider(Protocol):
    def get_rate(self) -> Decimal:
        """CRC por 1 USD. Lanza ExchangeRateUnavailable si el servicio falla."""
        ...


class HttpExchangeRateProvider:
    """Consulta un servicio HTTP público (por defecto open.er-api.com) y toma rates["CRC"]. Solo producción.

    Cualquier fallo (red, timeout, HTTP != 2xx, JSON o campo ausente, valor no numérico) -> ExchangeRateUnavailable.
    """

    def __init__(self, url: str = DEFAULT_EXCHANGE_RATE_URL, timeout: float = HTTP_TIMEOUT_SECONDS) -> None:
        self._url = url
        self._timeout = timeout

    def get_rate(self) -> Decimal:
        try:
            response = httpx.get(self._url, timeout=self._timeout)
            response.raise_for_status()
            value = Decimal(str(response.json()["rates"]["CRC"]))
        except (httpx.HTTPError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
            raise ExchangeRateUnavailable("Servicio de tipo de cambio no disponible") from exc
        if not value.is_finite() or value <= 0:
            raise ExchangeRateUnavailable("El servicio devolvió una tasa inválida")
        return value


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
