"""Rutas de ofertas (contrato §5). Delgadas: la lógica está en app/services/offers.py."""
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, require_user
from app.models import Offer
from app.rules.money import format_money
from app.rules.timeutil import to_iso_utc
from app.services import offers as service

router = APIRouter(tags=["offers"], dependencies=[Depends(require_user)])


class OfferIn(BaseModel):
    provider_id: int
    amount: Any  # string decimal; el formato lo valida el service (mismos errores que la UI)


class OfferUpdate(BaseModel):
    amount: Any


def offer_out(o: Offer) -> dict:
    return {
        "id": o.id,
        "tender_id": o.tender_id,
        "provider_id": o.provider_id,
        "amount": format_money(o.amount_cents),
        "created_at": to_iso_utc(o.created_at),
    }


@router.post("/tenders/{tender_id}/offers", status_code=201)
def create_offer(tender_id: int, data: OfferIn, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return offer_out(service.create_offer(db, clock, tender_id, data.provider_id, data.amount))


@router.get("/tenders/{tender_id}/offers")
def list_offers(tender_id: int, db: Session = Depends(get_db)):
    return [offer_out(o) for o in service.list_offers(db, tender_id)]


@router.get("/offers/{offer_id}")
def get_offer(offer_id: int, db: Session = Depends(get_db)):
    return offer_out(service.get_offer(db, offer_id))


@router.put("/offers/{offer_id}")
def update_offer(offer_id: int, data: OfferUpdate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return offer_out(service.update_offer(db, clock, offer_id, data.amount))


@router.delete("/offers/{offer_id}", status_code=204)
def delete_offer(offer_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)) -> Response:
    service.delete_offer(db, clock, offer_id)
    return Response(status_code=204)
