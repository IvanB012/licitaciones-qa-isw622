"""Casos de uso de rangos de aprobación (REQ-009). Los usan la API y la UI.

Solo el CRUD y la validación de traslapes: determinar el aprobador de una oferta es del módulo de evaluación.
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import Conflict, NotFound
from app.models import ApprovalRange
from app.rules import approval_ranges as rules

DUPLICATE_MSG = "Ya existe un rango para ese nivel de aprobación."


def get_range(db: Session, range_id: int) -> ApprovalRange:
    row = db.get(ApprovalRange, range_id)
    if row is None:
        raise NotFound("El rango de aprobación no existe.")
    return row


def list_ranges(db: Session) -> list[ApprovalRange]:
    return list(db.scalars(select(ApprovalRange).order_by(ApprovalRange.min_cents, ApprovalRange.id)))


def _check_unique_and_disjoint(db: Session, candidate: rules.Range, exclude_id: int | None) -> None:
    others = [r for r in list_ranges(db) if r.id != exclude_id]  # al editar se ignora el propio
    if any(r.level == candidate.level for r in others):
        raise Conflict(DUPLICATE_MSG, code="duplicado")
    clash = rules.find_overlap(candidate, (rules.Range(r.level, r.min_cents, r.max_cents) for r in others))
    if clash is not None:
        raise Conflict(f"El rango se traslapa con el de {clash.level}.", code="rango_traslapado")


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:  # UNIQUE(level) de la BD: mismo error que el chequeo previo
        db.rollback()
        raise Conflict(DUPLICATE_MSG, code="duplicado") from None


def create_range(db: Session, *, level: object, min: object, max: object = None) -> ApprovalRange:
    candidate = rules.validate_range(level, min, max)
    _check_unique_and_disjoint(db, candidate, None)
    row = ApprovalRange(level=candidate.level, min_cents=candidate.min_cents, max_cents=candidate.max_cents)
    db.add(row)
    _commit(db)
    return row


def update_range(db: Session, range_id: int, *, level: object, min: object, max: object = None) -> ApprovalRange:
    row = get_range(db, range_id)
    candidate = rules.validate_range(level, min, max)
    _check_unique_and_disjoint(db, candidate, row.id)
    row.level, row.min_cents, row.max_cents = candidate.level, candidate.min_cents, candidate.max_cents
    _commit(db)
    return row


def delete_range(db: Session, range_id: int) -> None:
    """Borrar nunca crea un traslape (contrato §10), así que siempre se permite."""
    db.delete(get_range(db, range_id))
    db.commit()
