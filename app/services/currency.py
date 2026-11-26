"""Tasa de cambio para MOSTRAR importes (REQ-010). Solo lectura: nunca escribe en la BD.

Contrato §5 (/exchange-rates/current): última tasa guardada; si no hay ninguna, 500.00 con fuente 'seed'.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.models import ExchangeRate
from app.rules.constants import RATE_SOURCE_SEED
from app.rules.money import rate_from_x10000
from app.rules.timeutil import official_date

FALLBACK_RATE = Decimal("500.00")
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class DisplayRate:
    rate: Decimal  # CRC por USD
    rate_date: date
    source: str

    @property
    def text(self) -> str:
        """500.00 si es exacta a 2 decimales; si no, hasta 4 decimales (512.3456)."""
        two = self.rate.quantize(_CENT)
        return format(two if two == self.rate else self.rate.normalize(), "f")


def current_rate(db: Session, clock: Clock) -> DisplayRate:
    row = db.scalar(select(ExchangeRate).order_by(ExchangeRate.rate_date.desc(), ExchangeRate.id.desc()).limit(1))
    if row is None:
        return DisplayRate(FALLBACK_RATE, official_date(clock.now()), RATE_SOURCE_SEED)
    return DisplayRate(rate_from_x10000(row.rate_x10000), row.rate_date, row.source)
