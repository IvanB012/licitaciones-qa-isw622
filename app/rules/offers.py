"""Reglas puras de ofertas (REQ-004, REQ-005). Sin BD, sin red, sin reloj implícito: ``now`` llega por parámetro."""
from datetime import datetime

from app.errors import Conflict, ValidationFailed
from app.rules.constants import STATUS_PUBLICADA
from app.rules.money import format_display, parse_money


def check_tender_open(status: str, closes_at: datetime, now: datetime) -> None:
    """REQ-004: solo se ofertan licitaciones Publicadas y ANTES del cierre.

    ``now >= closes_at`` rechaza: exactamente en el instante de cierre ya no se acepta.
    El estado se revisa primero (una Borrador/Cerrada es ``licitacion_no_publicada`` aunque su fecha no haya vencido).
    """
    if status != STATUS_PUBLICADA:
        raise Conflict(
            f"La licitación está en estado {status}; solo se aceptan ofertas en licitaciones Publicadas.",
            code="licitacion_no_publicada",
        )
    if now > closes_at:
        raise Conflict("La licitación ya cerró: venció el plazo para presentar ofertas.", code="licitacion_vencida")


def parse_amount(text: object, budget_cents: int) -> int:
    """REQ-005: monto de la oferta en céntimos. Formato válido, > 0 y <= presupuesto (igual al presupuesto es válido).

    Formato/cero/negativo -> ``monto_invalido``. Superior al presupuesto (aunque sea un céntimo) -> ``monto_excede_presupuesto``.
    """
    cents = parse_money(text)
    if cents <= 0:
        raise ValidationFailed("El monto de la oferta debe ser mayor que cero.", code="monto_invalido")
    if cents > budget_cents:
        raise ValidationFailed(
            f"El monto de la oferta no puede superar el presupuesto de la licitación ({format_display(budget_cents)}).",
            code="monto_excede_presupuesto",
        )
    return cents
