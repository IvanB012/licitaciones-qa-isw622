"""Rutas de proveedores (contrato §5). Delgadas: toda la lógica está en app/services/providers.py."""
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.clock import Clock
from app.deps import get_clock, get_db, require_user
from app.models import Provider
from app.services import providers as service

router = APIRouter(prefix="/providers", tags=["providers"], dependencies=[Depends(require_user)])


class ProviderIn(BaseModel):
    # Any: el formato lo valida el service (mismos errores que la UI).
    name: Any
    contact_email: Any = None


def provider_out(p: Provider) -> dict:
    return {"id": p.id, "name": p.name, "contact_email": p.contact_email}


@router.post("", status_code=201)
def create_provider(data: ProviderIn, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return provider_out(service.create_provider(db, clock, **data.model_dump()))


@router.get("")
def list_providers(db: Session = Depends(get_db)):
    return [provider_out(p) for p in service.list_providers(db)]


@router.get("/{provider_id}")
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    return provider_out(service.get_provider(db, provider_id))


@router.put("/{provider_id}")
def update_provider(provider_id: int, data: ProviderIn, db: Session = Depends(get_db)):
    return provider_out(service.update_provider(db, provider_id, **data.model_dump()))


@router.delete("/{provider_id}", status_code=204)
def delete_provider(provider_id: int, db: Session = Depends(get_db)) -> Response:
    service.delete_provider(db, provider_id)
    return Response(status_code=204)
