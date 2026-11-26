"""Reloj inyectable (contrato §11). Todo el código obtiene la hora de Clock.now()."""
from datetime import datetime, timedelta, timezone
from typing import Protocol

from fastapi import Request


class Clock(Protocol):
    def now(self) -> datetime:
        """Instante actual, aware, en UTC."""
        ...


class SystemClock:
    """Reloj real (producción)."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FakeClock:
    """Reloj controlable para pruebas (antes / exactamente en / después del cierre)."""

    DEFAULT_START = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)

    def __init__(self, start: datetime | None = None) -> None:
        self._now = self._check(start or self.DEFAULT_START)

    @staticmethod
    def _check(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("FakeClock requiere datetime con zona horaria")
        return value.astimezone(timezone.utc)

    def now(self) -> datetime:
        return self._now

    def set(self, value: datetime) -> None:
        self._now = self._check(value)

    def advance(self, delta: timedelta | None = None, **kwargs: float) -> datetime:
        """Avanza el reloj: ``advance(timedelta(hours=1))`` o ``advance(seconds=30)``."""
        self._now = self._now + (delta if delta is not None else timedelta(**kwargs))
        return self._now


def get_clock(request: Request) -> Clock:
    """Dependencia FastAPI. Se inyecta en create_app(clock=...) o con app.dependency_overrides."""
    return request.app.state.clock
