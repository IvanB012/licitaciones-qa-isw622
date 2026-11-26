"""Rutas de rangos de aprobación (contrato §5). TODAS solo admin: el operador recibe 403 `prohibido`."""
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import ApprovalRange
from app.rules.money import format_money
from app.services import approval_ranges as service

router = APIRouter(prefix="/approval-ranges", tags=["approval-ranges"], dependencies=[Depends(require_admin)])


class RangeIn(BaseModel):
    # Any: nivel y montos los valida el service (mismos errores que la UI).
    level: Any
    min: Any  # string decimal, p. ej. "1000000.00"
    max: Any = None  # string decimal o null (sin tope)


def range_out(r: ApprovalRange) -> dict:
    return {
        "id": r.id,
        "level": r.level,
        "min": format_money(r.min_cents),
        "max": None if r.max_cents is None else format_money(r.max_cents),
    }


@router.post("", status_code=201)
def create_range(data: RangeIn, db: Session = Depends(get_db)):
    return range_out(service.create_range(db, **data.model_dump()))


@router.get("")
def list_ranges(db: Session = Depends(get_db)):
    return [range_out(r) for r in service.list_ranges(db)]


@router.get("/{range_id}")
def get_range(range_id: int, db: Session = Depends(get_db)):
    return range_out(service.get_range(db, range_id))


@router.put("/{range_id}")
def update_range(range_id: int, data: RangeIn, db: Session = Depends(get_db)):
    return range_out(service.update_range(db, range_id, **data.model_dump()))


@router.delete("/{range_id}", status_code=204)
def delete_range(range_id: int, db: Session = Depends(get_db)) -> Response:
    service.delete_range(db, range_id)
    return Response(status_code=204)
