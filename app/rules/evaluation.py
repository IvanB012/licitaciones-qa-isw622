"""Reglas puras de evaluación (REQ-007, REQ-008, REQ-009, REQ-010). Sin BD, sin red, sin float.

Todos los montos son céntimos CRC (int). La clasificación del ahorro se decide con aritmética ENTERA sobre el valor
exacto: el porcentaje mostrado (2 decimales) solo es presentación y nunca decide la clasificación.
"""
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, TypeVar

from app.errors import Conflict, ValidationFailed
from app.rules.approval_ranges import Range
from app.rules.constants import CURRENCIES
from app.rules.money import format_display

NO_OFFERS_MESSAGE = "Sin ofertas válidas"
CLASS_CONVENIENTE = "Conveniente"
CLASS_ACEPTABLE = "Aceptable"
CLASS_SIN_AHORRO = "Válida sin ahorro"

_PCT_STEP = Decimal("0.01")
_T = TypeVar("_T")


def parse_currency(value: object) -> str:
    """Moneda de la vista: CRC (por defecto) o USD, sin distinguir mayúsculas. Otra cosa -> 422."""
    if value is None:
        return "CRC"
    code = value.strip().upper() if isinstance(value, str) else ""
    if code not in CURRENCIES:
        raise ValidationFailed(f"Moneda inválida. Valores permitidos: {', '.join(CURRENCIES)}.", code="validacion")
    return code


def pick_best(offers: Iterable[_T]) -> _T | None:
    """REQ-007: la menor oferta gana; en empate la registrada primero (``created_at``), luego la de menor ``id``.

    Cada oferta debe exponer ``amount_cents``, ``created_at`` e ``id``. Sin ofertas devuelve None.
    """
    best: Any = None
    for offer in offers:
        if best is None or _rank(offer) < _rank(best):
            best = offer
    return best


def _rank(offer: Any) -> tuple:
    return (offer.amount_cents, offer.created_at, offer.id)


def _check_amounts(budget_cents: int, best_cents: int) -> None:
    if budget_cents <= 0 or not 0 < best_cents <= budget_cents:
        raise ValueError("se requiere presupuesto > 0 y 0 < mejor oferta <= presupuesto")


def savings_pct(budget_cents: int, best_cents: int) -> Decimal:
    """REQ-008: ((presupuesto - mejor oferta) / presupuesto) x 100, a 2 decimales ROUND_HALF_UP (solo para mostrar)."""
    _check_amounts(budget_cents, best_cents)
    pct = Decimal(budget_cents - best_cents) * 100 / Decimal(budget_cents)
    return pct.quantize(_PCT_STEP, rounding=ROUND_HALF_UP)


def classify_savings(budget_cents: int, best_cents: int) -> str:
    """REQ-008 sobre el valor EXACTO (sin redondear): >= 10 % Conveniente; > 0 y < 10 % Aceptable; 0 % Válida sin ahorro.

    ahorro >= 10 %  <=>  (presupuesto - mejor) x 100 >= 10 x presupuesto  <=>  (presupuesto - mejor) x 10 >= presupuesto.
    """
    _check_amounts(budget_cents, best_cents)
    diff = budget_cents - best_cents
    if diff * 10 >= budget_cents:
        return CLASS_CONVENIENTE
    return CLASS_ACEPTABLE if diff > 0 else CLASS_SIN_AHORRO


def approver_for(amount_cents: int, ranges: Iterable[Range]) -> str:
    """REQ-009: nivel cuyo rango semiabierto [min, max) contiene el monto (max None = sin tope).

    Sin rango que lo contenga (configuración con huecos) -> 409 ``sin_rango_aprobacion``.
    """
    for r in sorted(ranges, key=lambda r: r.min_cents):
        if r.min_cents <= amount_cents and (r.max_cents is None or amount_cents < r.max_cents):
            return r.level
    raise Conflict(
        f"No hay un rango de aprobación configurado para el monto {format_display(amount_cents)}.",
        code="sin_rango_aprobacion",
    )
