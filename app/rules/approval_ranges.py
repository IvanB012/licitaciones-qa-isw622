"""Reglas puras de rangos de aprobación (REQ-009, contrato §6). Sin BD ni red.

Intervalos semiabiertos [min, max) en céntimos; max nulo = sin tope (infinito).
Rangos adyacentes ([1, 100000000) y [100000000, 1000000000)) NO se traslapan; los huecos se permiten.
"""
from collections.abc import Iterable
from dataclasses import dataclass

from app.errors import ValidationFailed
from app.rules.constants import APPROVAL_LEVELS
from app.rules.money import parse_money

CODE_INVALID = "rango_invalido"


@dataclass(frozen=True)
class Range:
    level: str
    min_cents: int
    max_cents: int | None  # exclusivo; None = sin tope


def _cents(value: object, what: str) -> int:
    """Texto decimal -> céntimos. Un formato inválido también es rango_invalido (422)."""
    try:
        return parse_money(value)
    except ValidationFailed as exc:
        raise ValidationFailed(f"{what}: {exc.detalle}", code=CODE_INVALID) from None


def validate_range(level: object, min_value: object, max_value: object) -> Range:
    """Nivel entre los 3 permitidos, min >= 1 céntimo, max nulo o > min."""
    if level not in APPROVAL_LEVELS:
        raise ValidationFailed(f"Nivel inválido. Valores: {', '.join(APPROVAL_LEVELS)}.", code=CODE_INVALID)
    min_cents = _cents(min_value, "El mínimo")
    if min_cents < 1:
        raise ValidationFailed("El mínimo debe ser al menos 0.01 (un céntimo).", code=CODE_INVALID)
    max_cents = None
    if not (max_value is None or (isinstance(max_value, str) and not max_value.strip())):
        max_cents = _cents(max_value, "El máximo")
        if max_cents <= min_cents:
            raise ValidationFailed("El máximo debe ser mayor que el mínimo.", code=CODE_INVALID)
    return Range(level, min_cents, max_cents)


def overlaps(a: Range, b: Range) -> bool:
    """a y b se traslapan si a.min < b.max_efectivo y b.min < a.max_efectivo (None = infinito)."""
    a_starts_before_b_ends = b.max_cents is None or a.min_cents < b.max_cents
    b_starts_before_a_ends = a.max_cents is None or b.min_cents < a.max_cents
    return a_starts_before_b_ends and b_starts_before_a_ends


def find_overlap(candidate: Range, others: Iterable[Range]) -> Range | None:
    """Primer rango de ``others`` que se traslapa con ``candidate`` (None si no hay)."""
    return next((other for other in others if overlaps(candidate, other)), None)
