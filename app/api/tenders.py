"""Rutas de licitaciones (contrato §5). Delgadas: toda la lógica está en app/services/tenders.py."""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, require_user
from app.models import Tender
from app.rules.money import format_money
from app.rules.timeutil import to_iso_utc
from app.services import tenders as service

router = APIRouter(prefix="/tenders", tags=["tenders"], dependencies=[Depends(require_user)])


class TenderIn(BaseModel):
    # Any: el formato del dinero y de los textos lo valida el service (mismos errores que la UI).
    code: Any
    title: Any
    description: Any = None
    budget: Any  # string decimal, p. ej. "10000000.00"
    closes_at: datetime  # ISO-8601 con zona, p. ej. "2026-11-28T18:00:00Z"


def tender_out(t: Tender) -> dict:
    return {
        "id": t.id,
        "code": t.code,
        "title": t.title,
        "description": t.description,
        "budget": format_money(t.budget_cents),
        "closes_at": to_iso_utc(t.closes_at),
        "status": t.status,
        "created_at": to_iso_utc(t.created_at),
    }


@router.post("", status_code=201)
def create_tender(data: TenderIn, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return tender_out(service.create_tender(db, clock, **data.model_dump()))


@router.get("")
def list_tenders(status: str | None = None, db: Session = Depends(get_db)):
    return [tender_out(t) for t in service.list_tenders(db, status)]


@router.get("/{tender_id}")
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    return tender_out(service.get_tender(db, tender_id))


@router.put("/{tender_id}")
def update_tender(tender_id: int, data: TenderIn, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return tender_out(service.update_tender(db, clock, tender_id, **data.model_dump()))


@router.delete("/{tender_id}", status_code=204)
def delete_tender(tender_id: int, db: Session = Depends(get_db)) -> Response:
    service.delete_tender(db, tender_id)
    return Response(status_code=204)


@router.post("/{tender_id}/publish")
def publish_tender(tender_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return tender_out(service.publish_tender(db, clock, tender_id))


@router.post("/{tender_id}/close")
def close_tender(tender_id: int, db: Session = Depends(get_db)):
    return tender_out(service.close_tender(db, tender_id))
