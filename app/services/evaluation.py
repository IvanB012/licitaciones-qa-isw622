"""Caso de uso de evaluación de una licitación (REQ-007..REQ-010). Solo lectura: nunca escribe en la BD.

Reutiliza: ofertas (services.offers), rangos de aprobación (services.approval_ranges, tabla configurable)
y tasa vigente (services.currency). No duplica ninguna de esas reglas.
"""
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.clock import Clock
from app.errors import Conflict
from app.models import Offer, Tender
from app.rules import evaluation as rules
from app.rules.approval_ranges import Range
from app.rules.money import crc_to_usd, format_money
from app.services import approval_ranges as ranges_service
from app.services import offers as offers_service
from app.services.currency import DisplayRate, current_rate
from app.services.tenders import get_tender


@dataclass(frozen=True)
class Evaluation:
    tender: Tender
    currency: str  # CRC | USD (solo vista)
    offers_count: int
    best: Offer | None
    message: str
    savings_pct: Decimal | None
    classification: str | None
    approver: str | None
    approver_warning: str | None  # solo con strict=False: por qué no hay aprobador (UI)
    rate: DisplayRate | None  # solo en USD

    @property
    def savings_pct_text(self) -> str | None:
        return None if self.savings_pct is None else format(self.savings_pct, "f")

    @property
    def best_amount_text(self) -> str | None:
        """Monto de la mejor oferta en la moneda pedida: '9000000.00' (CRC) o '18000.00' (USD)."""
        if self.best is None:
            return None
        if self.rate is None:
            return format_money(self.best.amount_cents)
        return format(crc_to_usd(self.best.amount_cents, self.rate.rate), "f")


def evaluate(db: Session, clock: Clock, tender_id: int, currency: object = "CRC", *, strict: bool = True) -> Evaluation:
    """Mejor oferta, ahorro, clasificación y aprobador de una licitación.

    strict=True (API): sin rango de aprobación para el monto -> 409 ``sin_rango_aprobacion``.
    strict=False (UI): no falla; devuelve el resto y el motivo en ``approver_warning``.
    """
    cur = rules.parse_currency(currency)
    tender = get_tender(db, tender_id)  # 404
    offers = offers_service.list_offers(db, tender.id)
    rate = current_rate(db, clock) if cur == "USD" else None
    best = rules.pick_best(offers)

    if best is None:
        return Evaluation(tender, cur, 0, None, rules.NO_OFFERS_MESSAGE, None, None, None, None, rate)

    approver: str | None = None
    warning: str | None = None
    try:
        ranges = [Range(r.level, r.min_cents, r.max_cents) for r in ranges_service.list_ranges(db)]
        approver = rules.approver_for(best.amount_cents, ranges)
    except Conflict as exc:
        if strict:
            raise
        warning = exc.detalle

    return Evaluation(
        tender=tender,
        currency=cur,
        offers_count=len(offers),
        best=best,
        message=f"Mejor oferta: {best.provider.name}",
        savings_pct=rules.savings_pct(tender.budget_cents, best.amount_cents),
        classification=rules.classify_savings(tender.budget_cents, best.amount_cents),
        approver=approver,
        approver_warning=warning,
        rate=rate,
    )
