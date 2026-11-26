"""Casos de uso de ofertas (REQ-004, REQ-005, REQ-006). Los usan la API y la UI.

Orden de validación al crear (contrato §5): existe licitación -> existe proveedor -> Publicada -> no vencida
-> formato/monto -> duplicado. La BD respalda con UNIQUE/CHECK (nunca llega un 500).
El proveedor se consulta directamente del modelo: este módulo no depende del service de proveedores.
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock
from app.errors import Conflict, NotFound
from app.models import Offer, Provider
from app.rules import offers as rules
from app.services.tenders import get_tender

DUPLICATE_MSG = "Este proveedor ya presentó una oferta en esta licitación."


def get_offer(db: Session, offer_id: int) -> Offer:
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise NotFound("La oferta no existe.")
    return offer


def list_offers(db: Session, tender_id: int) -> list[Offer]:
    """Ofertas de una licitación en orden de registro (created_at, luego id)."""
    get_tender(db, tender_id)  # 404 si no existe
    return list(
        db.scalars(select(Offer).where(Offer.tender_id == tender_id).order_by(Offer.created_at, Offer.id))
    )


def list_provider_options(db: Session) -> list[Provider]:
    """Proveedores para el selector del formulario de oferta."""
    return list(db.scalars(select(Provider).order_by(Provider.name)))


def _offer_exists(db: Session, tender_id: int, provider_id: int) -> bool:
    return (
        db.scalar(select(Offer.id).where(Offer.tender_id == tender_id, Offer.provider_id == provider_id)) is not None
    )


def create_offer(db: Session, clock: Clock, tender_id: int, provider_id: int, amount: object) -> Offer:
    now = clock.now()
    tender = get_tender(db, tender_id)  # 404
    if db.get(Provider, provider_id) is None:
        raise NotFound("El proveedor no existe.")
    rules.check_tender_open(tender.status, tender.closes_at, now)  # 409 no publicada / vencida
    amount_cents = rules.parse_amount(amount, tender.budget_cents)  # 422
    if _offer_exists(db, tender.id, provider_id):
        raise Conflict(DUPLICATE_MSG, code="oferta_duplicada")
    offer = Offer(tender_id=tender.id, provider_id=provider_id, amount_cents=amount_cents, created_at=now)
    db.add(offer)
    try:
        db.commit()
    except IntegrityError:  # UNIQUE (tender_id, provider_id) de la BD: mismo error que el chequeo previo
        db.rollback()
        raise Conflict(DUPLICATE_MSG, code="oferta_duplicada") from None
    return offer


def update_offer(db: Session, clock: Clock, offer_id: int, amount: object) -> Offer:
    """Cambia el monto con las mismas reglas que al crear. No cambia created_at (el desempate REQ-007 no se altera)."""
    offer = get_offer(db, offer_id)
    tender = offer.tender
    rules.check_tender_open(tender.status, tender.closes_at, clock.now())
    offer.amount_cents = rules.parse_amount(amount, tender.budget_cents)
    db.commit()
    return offer


def delete_offer(db: Session, clock: Clock, offer_id: int) -> None:
    """Solo mientras la licitación siga abierta (Publicada y no vencida)."""
    offer = get_offer(db, offer_id)
    rules.check_tender_open(offer.tender.status, offer.tender.closes_at, clock.now())
    db.delete(offer)
    db.commit()
