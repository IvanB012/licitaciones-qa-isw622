"""Zona horaria de presentación (contrato §1): Costa Rica, UTC−6 fijo (sin horario de verano)."""
from datetime import date, datetime, timedelta, timezone

CR_TZ = timezone(timedelta(hours=-6), "America/Costa_Rica")


def to_cr(moment: datetime) -> datetime:
    """Convierte un instante aware (UTC en BD/API) a hora de Costa Rica para mostrarlo."""
    if moment.tzinfo is None:
        raise ValueError("se requiere un datetime con zona horaria (UTC)")
    return moment.astimezone(CR_TZ)


def from_cr(local: datetime) -> datetime:
    """Interpreta un datetime SIN zona (lo que escribe el usuario en un formulario) como hora de Costa Rica y lo pasa a UTC."""
    if local.tzinfo is not None:
        raise ValueError("se esperaba un datetime sin zona horaria (hora local de Costa Rica)")
    return local.replace(tzinfo=CR_TZ).astimezone(timezone.utc)


def to_iso_utc(moment: datetime) -> str:
    """Instante aware -> ISO-8601 UTC con 'Z' (formato de la API): 2026-11-27T18:00:00Z."""
    if moment.tzinfo is None:
        raise ValueError("se requiere un datetime con zona horaria")
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def official_date(now: datetime) -> date:
    """Fecha oficial del sistema = fecha (hora de Costa Rica) del instante del Clock."""
    return to_cr(now).date()
