"""Casos de uso de proveedores (REQ-001, REQ-012). Los usan la API y la UI: las validaciones viven aquí y en app/rules."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock
from app.errors import Conflict, NotFound
from app.models import Offer, Provider
from app.rules import providers as rules
from app.rules.normalization import normalize_name

DUPLICATE_MSG = "Ya existe un proveedor con ese nombre."


def get_provider(db: Session, provider_id: int) -> Provider:
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise NotFound("El proveedor no existe.")
    return provider


def list_providers(db: Session) -> list[Provider]:
    return list(db.scalars(select(Provider).order_by(Provider.name_key, Provider.id)))


def _validated_fields(name: object, contact_email: object) -> dict:
    clean = rules.clean_name(name)
    return {"name": clean, "name_key": normalize_name(clean), "contact_email": rules.clean_email(contact_email)}


def _name_taken(db: Session, name_key: str, exclude_id: int | None = None) -> bool:
    query = select(Provider.id).where(Provider.name_key == name_key)
    if exclude_id is not None:
        query = query.where(Provider.id != exclude_id)
    return db.scalar(query) is not None


def _commit(db: Session) -> None:
    """Commit; la restricción UNIQUE de la BD también se traduce a 409 (nunca 500)."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict(DUPLICATE_MSG, code="duplicado") from None


def create_provider(db: Session, clock: Clock, *, name: object, contact_email: object = None) -> Provider:
    fields = _validated_fields(name, contact_email)
    if _name_taken(db, fields["name_key"]):
        raise Conflict(DUPLICATE_MSG, code="duplicado")
    provider = Provider(**fields, created_at=clock.now())
    db.add(provider)
    _commit(db)
    return provider


def update_provider(db: Session, provider_id: int, *, name: object, contact_email: object = None) -> Provider:
    provider = get_provider(db, provider_id)
    fields = _validated_fields(name, contact_email)
    if _name_taken(db, fields["name_key"], exclude_id=provider.id):  # ignora al propio registro
        raise Conflict(DUPLICATE_MSG, code="duplicado")
    for key, value in fields.items():
        setattr(provider, key, value)
    _commit(db)
    return provider


def delete_provider(db: Session, provider_id: int) -> None:
    provider = get_provider(db, provider_id)
    offers = db.scalar(select(func.count()).select_from(Offer).where(Offer.provider_id == provider.id)) or 0
    if offers:
        raise Conflict("El proveedor tiene ofertas y no se puede borrar.", code="en_uso")
    db.delete(provider)
    db.commit()
