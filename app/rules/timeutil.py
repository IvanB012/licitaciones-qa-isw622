"""Zona horaria de presentación (contrato §1): Costa Rica, UTC−6 fijo (sin horario de verano)."""
from datetime import date, datetime, timedelta, timezone

CR_TZ = timezone(timedelta(hours=-6), "America/Costa_Rica")


def to_cr(moment: datetime) -> datetime:
    """Convierte un instante aware (UTC en BD/API) a hora de Costa Rica para mostrarlo."""
    if moment.tzinfo is None:
        raise ValueError("se requiere un datetime con zona horaria (UTC)")
    return moment.astimezone(CR_TZ)


def official_date(now: datetime) -> date:
    """Fecha oficial del sistema = fecha (hora de Costa Rica) del instante del Clock."""
    return to_cr(now).date()
