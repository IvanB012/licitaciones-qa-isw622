"""Reglas puras del tipo de cambio (REQ-010). Sin BD, sin red; la hora llega como parámetro (Clock.now())."""
from datetime import date, datetime

from app.errors import ValidationFailed
from app.rules.constants import RATE_SOURCE_MANUAL, RATE_SOURCE_SUGERIDA
from app.rules.money import CODE_RATE, parse_rate, rate_to_x10000
from app.rules.timeutil import official_date

# Fuentes que un usuario puede indicar al guardar. 'seed' solo lo pone el seed.
USER_SOURCES = (RATE_SOURCE_MANUAL, RATE_SOURCE_SUGERIDA)
MAX_RATE_X10000 = 2**63 - 1  # límite del entero de la BD (SQLite INTEGER de 64 bits)


def parse_rate_x10000(text: object) -> int:
    """Tasa CRC por USD como texto -> entero x10 000. > 0, solo dígitos y punto, hasta 4 decimales (tasa_invalida)."""
    if not isinstance(text, str):
        raise ValidationFailed("La tasa debe enviarse como texto decimal, p. ej. \"500.00\".", code=CODE_RATE)
    scaled = rate_to_x10000(parse_rate(text))
    if scaled > MAX_RATE_X10000:
        raise ValidationFailed("La tasa es demasiado grande.", code=CODE_RATE)
    return scaled


def parse_rate_date(value: object, now: datetime, existing: date | None = None) -> date:
    """Fecha de la tasa. Vacía -> la fecha oficial del Clock. Debe ser la oficial (otra fecha -> tasa_invalida).

    ``existing``: al EDITAR se admite además conservar la fecha que el registro ya tenía.
    """
    official = official_date(now)
    if value is None or (isinstance(value, str) and not value.strip()):
        return official
    if isinstance(value, datetime):
        raise ValidationFailed("La fecha de la tasa no es válida.", code=CODE_RATE)
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value.strip())
        except ValueError:
            raise ValidationFailed("La fecha de la tasa no es válida (use AAAA-MM-DD).", code=CODE_RATE) from None
    if not isinstance(value, date):
        raise ValidationFailed("La fecha de la tasa no es válida.", code=CODE_RATE)
    if value != official and value != existing:
        raise ValidationFailed(
            f"La fecha de la tasa debe ser la fecha oficial del sistema ({official.isoformat()}).", code=CODE_RATE
        )
    return value


def check_source(source: object) -> str:
    """Fuente al guardar: 'manual' (por defecto) o 'sugerida'."""
    if source is None:
        return RATE_SOURCE_MANUAL
    if source not in USER_SOURCES:
        raise ValidationFailed(f"Fuente inválida. Valores: {', '.join(USER_SOURCES)}.", code=CODE_RATE)
    return source
