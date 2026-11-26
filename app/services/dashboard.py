"""Resumen de solo lectura para el panel '/'."""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Offer, Provider, Tender
from app.rules.constants import STATUS_PUBLICADA


@dataclass
class DashboardSummary:
    providers: int
    tenders: int
    published_tenders: int
    offers: int
    recent_tenders: list[Tender]


def get_dashboard_summary(db: Session, recent: int = 5) -> DashboardSummary:
    def count(model, *where) -> int:
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    recent_tenders = list(db.scalars(select(Tender).order_by(Tender.created_at.desc(), Tender.id.desc()).limit(recent)))
    return DashboardSummary(
        providers=count(Provider),
        tenders=count(Tender),
        published_tenders=count(Tender, Tender.status == STATUS_PUBLICADA),
        offers=count(Offer),
        recent_tenders=recent_tenders,
    )
