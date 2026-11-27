"""GET /api/tenders/{id}/evaluation (contrato §5). Solo lectura; la lógica está en app/services/evaluation.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, require_user
from app.rules.money import format_money
from app.services import evaluation as service

router = APIRouter(prefix="/tenders", tags=["evaluation"], dependencies=[Depends(require_user)])


def evaluation_out(ev: service.Evaluation) -> dict:
    best = None
    if ev.best is not None:
        best = {"offer_id": ev.best.id, "provider_id": ev.best.provider_id, "amount": ev.best_amount_text}
    out = {
        "best_offer": best,
        "message": ev.message,
        "savings_pct": ev.savings_pct_text,
        "classification": ev.classification,
        "approver": ev.approver,
        "currency": ev.currency,
    }
    if ev.rate is not None:  # tasa y fecha utilizadas, solo al visualizar en USD (REQ-010)
        out["rate"] = ev.rate.text
        out["rate_date"] = ev.rate.rate_date.isoformat()
    return out


@router.get("/{tender_id}/evaluation")
def get_evaluation(
    tender_id: int, currency: str = "CRC", db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
):
    return evaluation_out(service.evaluate(db, clock, tender_id, currency))
