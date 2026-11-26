"""Reglas puras de licitaciones (REQ-002, REQ-003, REQ-004). Sin BD, sin red, sin reloj implícito:
la hora actual siempre llega como parámetro (viene de Clock.now()).
"""
from datetime import datetime

from app.errors import Conflict, ValidationFailed
from app.rules.constants import STATUS_BORRADOR, STATUS_CERRADA, STATUS_PUBLICADA
from app.rules.money import parse_money

# REQ-003: Borrador -> Publicada | Cerrada; Publicada -> Cerrada; Cerrada es terminal.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_BORRADOR: frozenset({STATUS_PUBLICADA, STATUS_CERRADA}),
    STATUS_PUBLICADA: frozenset({STATUS_CERRADA}),
    STATUS_CERRADA: frozenset(),
}


def clean_code(code: object) -> str:
    """Código recortado (REQ-002). Obligatorio. La unicidad se compara con normalize_code (code_key)."""
    if not isinstance(code, str) or not code.strip():
        raise ValidationFailed("El código de la licitación es obligatorio.", code="validacion_codigo")
    return code.strip()


def clean_title(title: object) -> str:
    """Título no vacío tras recortar espacios (REQ-002)."""
    if not isinstance(title, str) or not title.strip():
        raise ValidationFailed("El título de la licitación es obligatorio.", code="validacion_titulo")
    return title.strip()


def clean_description(description: object) -> str | None:
    """Descripción opcional: texto recortado o None si viene vacía."""
    if description is None:
        return None
    if not isinstance(description, str):
        raise ValidationFailed("La descripción debe ser texto.", code="validacion")
    return description.strip() or None


def parse_budget(text: object) -> int:
    """Presupuesto CRC en céntimos. Formato válido (money.parse_money) y > 0 (REQ-002)."""
    cents = parse_money(text)
    if cents <= 0:
        raise ValidationFailed("El presupuesto debe ser mayor que cero.", code="monto_invalido")
    return cents


def check_closes_in_future(closes_at: datetime, now: datetime) -> None:
    """Cierre estrictamente posterior a ``now`` (REQ-002). Igual o anterior -> cierre_no_futuro."""
    if closes_at.tzinfo is None:
        raise ValidationFailed("La fecha de cierre debe incluir zona horaria.", code="validacion")
    if closes_at <= now:
        raise ValidationFailed("La fecha y hora de cierre deben ser futuras.", code="cierre_no_futuro")


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def check_transition(current: str, target: str) -> None:
    """REQ-003: cualquier cambio de estado no permitido -> 409 transicion_invalida."""
    if not can_transition(current, target):
        raise Conflict(
            f"No se puede pasar una licitación de {current} a {target}.", code="transicion_invalida"
        )


def is_expired(status: str, closes_at: datetime, now: datetime) -> bool:
    """Publicada cuyo cierre ya llegó (``now >= closes_at``): sigue Publicada pero no acepta ofertas (REQ-004)."""
    return status == STATUS_PUBLICADA and now >= closes_at
