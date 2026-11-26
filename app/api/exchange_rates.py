"""Rutas de tipo de cambio (contrato §5). Delgadas: la lógica está en app/services/exchange_rates.py."""
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, get_rate_provider, require_user
from app.exchange import ExchangeRateProvider
from app.models import ExchangeRate
from app.services import exchange_rates as service
from app.services.currency import current_rate

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"], dependencies=[Depends(require_user)])


class RateIn(BaseModel):
    # Any: formato y reglas los valida el service (mismos errores que la UI).
    rate: Any  # string decimal, p. ej. "500.00" (hasta 4 decimales)
    rate_date: Any = None  # AAAA-MM-DD; por defecto la fecha oficial del Clock
    source: Any = None  # solo en POST: "manual" (defecto) | "sugerida"


class RateUpdate(BaseModel):
    rate: Any
    rate_date: Any = None


def rate_out(row: ExchangeRate) -> dict:
    return {
        "id": row.id,
        "rate": service.rate_text(row),
        "rate_date": row.rate_date.isoformat(),
        "source": row.source,
    }


@router.post("", status_code=201)
def create_rate(data: RateIn, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return rate_out(service.create_rate(db, clock, **data.model_dump()))


@router.get("")
def list_rates(db: Session = Depends(get_db)):
    return [rate_out(r) for r in service.list_rates(db)]


@router.get("/current")
def get_current(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    cur = current_rate(db, clock)
    return {"rate": cur.text, "rate_date": cur.rate_date.isoformat(), "source": cur.source}


@router.get("/suggest")
def suggest_rate(
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
    provider: ExchangeRateProvider = Depends(get_rate_provider),
):
    return service.suggest(db, clock, provider)  # solo sugiere: no guarda


@router.get("/{rate_id}")
def get_rate(rate_id: int, db: Session = Depends(get_db)):
    return rate_out(service.get_rate(db, rate_id))


@router.put("/{rate_id}")
def update_rate(rate_id: int, data: RateUpdate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return rate_out(service.update_rate(db, clock, rate_id, **data.model_dump()))


@router.delete("/{rate_id}", status_code=204)
def delete_rate(rate_id: int, db: Session = Depends(get_db)) -> Response:
    service.delete_rate(db, rate_id)
    return Response(status_code=204)
