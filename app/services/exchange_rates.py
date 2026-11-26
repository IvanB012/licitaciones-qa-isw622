"""Casos de uso del tipo de cambio (REQ-010). Los usan la API y la UI.

La tasa vigente (con respaldo 500.00 'seed') se lee con app.services.currency.current_rate: no se duplica aquí.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.errors import NotFound, ValidationFailed
from app.exchange import ExchangeRateProvider, ExchangeRateUnavailable
from app.models import ExchangeRate
from app.rules import exchange_rates as rules
from app.rules.money import rate_from_x10000, rate_to_x10000
from app.rules.timeutil import official_date
from app.services.currency import DisplayRate, current_rate

SOURCE_EXTERNO = "externo"
SOURCE_RESPALDO = "respaldo"
FALLBACK_NOTICE = "El servicio de tipo de cambio no está disponible. Se muestra la última tasa guardada como respaldo."


def rate_text(row: ExchangeRate) -> str:
    """Tasa guardada como string decimal (500.00; hasta 4 decimales si hace falta)."""
    return DisplayRate(rate_from_x10000(row.rate_x10000), row.rate_date, row.source).text


def get_rate(db: Session, rate_id: int) -> ExchangeRate:
    row = db.get(ExchangeRate, rate_id)
    if row is None:
        raise NotFound("El tipo de cambio no existe.")
    return row


def list_rates(db: Session) -> list[ExchangeRate]:
    """Más reciente primero (mismo orden con el que current_rate elige la vigente)."""
    return list(db.scalars(select(ExchangeRate).order_by(ExchangeRate.rate_date.desc(), ExchangeRate.id.desc())))


def create_rate(db: Session, clock: Clock, *, rate: object, rate_date: object = None, source: object = None) -> ExchangeRate:
    now = clock.now()
    row = ExchangeRate(
        rate_x10000=rules.parse_rate_x10000(rate),
        rate_date=rules.parse_rate_date(rate_date, now),
        source=rules.check_source(source),
        created_at=now,
    )
    db.add(row)
    db.commit()
    return row


def update_rate(db: Session, clock: Clock, rate_id: int, *, rate: object, rate_date: object = None) -> ExchangeRate:
    """Cambia tasa y fecha. La fecha debe ser la oficial o la que el registro ya tenía; la fuente no cambia."""
    row = get_rate(db, rate_id)
    row.rate_x10000 = rules.parse_rate_x10000(rate)
    row.rate_date = rules.parse_rate_date(rate_date if rate_date is not None else row.rate_date, clock.now(), row.rate_date)
    db.commit()
    return row


def delete_rate(db: Session, rate_id: int) -> None:
    """Se puede borrar: sin tasas guardadas el respaldo 500.00 cubre la ausencia (contrato §10)."""
    db.delete(get_rate(db, rate_id))
    db.commit()


def suggest(db: Session, clock: Clock, provider: ExchangeRateProvider) -> dict:
    """Consulta al proveedor externo. NO guarda nada: el usuario confirma creando la tasa.

    Si el servicio falla (o devuelve algo inutilizable) -> la última tasa guardada (o 500.00) con aviso y fuente 'respaldo'.
    """
    try:
        value = provider.get_rate()
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise ExchangeRateUnavailable("respuesta inválida del servicio")
        suggested = rate_from_x10000(rate_to_x10000(value))  # misma precisión (4 decimales) que se guarda
    except (ExchangeRateUnavailable, ValidationFailed):
        fallback = current_rate(db, clock)
        return {"rate": fallback.text, "source": SOURCE_RESPALDO, "aviso": FALLBACK_NOTICE}
    return {"rate": DisplayRate(suggested, official_date(clock.now()), SOURCE_EXTERNO).text, "source": SOURCE_EXTERNO}
