"""Casos de uso de licitaciones (REQ-002, REQ-003). Los usan la API y la UI: las validaciones viven aquí y en app/rules."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock
from app.errors import Conflict, NotFound, ValidationFailed
from app.models import Offer, Tender
from app.rules import tenders as rules
from app.rules.constants import STATUS_BORRADOR, STATUS_CERRADA, STATUS_PUBLICADA, TENDER_STATUSES
from app.rules.normalization import normalize_code

DUPLICATE_MSG = "Ya existe una licitación con ese código."


def get_tender(db: Session, tender_id: int) -> Tender:
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise NotFound("La licitación no existe.")
    return tender


def list_tenders(db: Session, status: str | None = None) -> list[Tender]:
    if status is not None and status not in TENDER_STATUSES:
        raise ValidationFailed(f"Estado inválido. Valores: {', '.join(TENDER_STATUSES)}.", code="validacion")
    query = select(Tender).order_by(Tender.created_at.desc(), Tender.id.desc())
    if status is not None:
        query = query.where(Tender.status == status)
    return list(db.scalars(query))


def _validated_fields(code: object, title: object, description: object, budget: object, closes_at: object, now: datetime) -> dict:
    """Validación común a crear y editar. Devuelve los campos listos para guardar."""
    clean_code = rules.clean_code(code)
    clean_title = rules.clean_title(title)
    clean_description = rules.clean_description(description)
    budget_cents = rules.parse_budget(budget)
    if not isinstance(closes_at, datetime):
        raise ValidationFailed("La fecha de cierre no es válida.", code="validacion")
    rules.check_closes_in_future(closes_at, now)
    return {
        "code": clean_code,
        "code_key": normalize_code(clean_code),
        "title": clean_title,
        "description": clean_description,
        "budget_cents": budget_cents,
        "closes_at": closes_at,
    }


def _code_taken(db: Session, code_key: str, exclude_id: int | None = None) -> bool:
    query = select(Tender.id).where(Tender.code_key == code_key)
    if exclude_id is not None:
        query = query.where(Tender.id != exclude_id)
    return db.scalar(query) is not None


def _commit(db: Session) -> None:
    """Commit; la restricción UNIQUE de la BD también se traduce a 409 (nunca 500)."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict(DUPLICATE_MSG, code="duplicado") from None


def create_tender(
    db: Session, clock: Clock, *, code: object, title: object, description: object = None, budget: object, closes_at: object
) -> Tender:
    now = clock.now()
    fields = _validated_fields(code, title, description, budget, closes_at, now)
    if _code_taken(db, fields["code_key"]):
        raise Conflict(DUPLICATE_MSG, code="duplicado")
    tender = Tender(**fields, status=STATUS_BORRADOR, created_at=now)
    db.add(tender)
    _commit(db)
    return tender


def update_tender(
    db: Session, clock: Clock, tender_id: int, *, code: object, title: object, description: object = None,
    budget: object, closes_at: object,
) -> Tender:
    tender = get_tender(db, tender_id)
    if tender.status != STATUS_BORRADOR:
        raise Conflict("Solo se puede editar una licitación en estado Borrador.", code="transicion_invalida")
    fields = _validated_fields(code, title, description, budget, closes_at, clock.now())
    if _code_taken(db, fields["code_key"], exclude_id=tender.id):
        raise Conflict(DUPLICATE_MSG, code="duplicado")
    for name, value in fields.items():
        setattr(tender, name, value)
    _commit(db)
    return tender


def delete_tender(db: Session, tender_id: int) -> None:
    tender = get_tender(db, tender_id)
    if tender.status != STATUS_BORRADOR:
        raise Conflict("Solo se puede borrar una licitación en estado Borrador.", code="en_uso")
    offers = db.scalar(select(func.count()).select_from(Offer).where(Offer.tender_id == tender.id)) or 0
    if offers:
        raise Conflict("La licitación tiene ofertas y no se puede borrar.", code="en_uso")
    db.delete(tender)
    db.commit()


def publish_tender(db: Session, clock: Clock, tender_id: int) -> Tender:
    """Borrador -> Publicada. Exige cierre futuro (REQ-002). Estado inválido -> 409 antes que el 422 de fecha."""
    tender = get_tender(db, tender_id)
    rules.check_transition(tender.status, STATUS_PUBLICADA)
    rules.check_closes_in_future(tender.closes_at, clock.now())
    tender.status = STATUS_PUBLICADA
    db.commit()
    return tender


def close_tender(db: Session, tender_id: int) -> Tender:
    """Borrador|Publicada -> Cerrada (manual). Cerrada es terminal (REQ-003)."""
    tender = get_tender(db, tender_id)
    rules.check_transition(tender.status, STATUS_CERRADA)
    tender.status = STATUS_CERRADA
    db.commit()
    return tender
