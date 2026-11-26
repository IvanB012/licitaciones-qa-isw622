"""Restricciones de BD del contrato §2 (UNIQUE, CHECK, FK). Aquí se prueba que la BD las hace cumplir."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from app.models import ApprovalRange, ExchangeRate, Offer, Provider, Tender, User

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


def _provider(name="Prov", key=None):
    return Provider(name=name, name_key=key or name.casefold(), created_at=NOW)


def _tender(code="LIC-1", key=None, **kw):
    data = dict(
        code=code, code_key=key or code.casefold(), title="T", budget_cents=100_000,
        closes_at=NOW + timedelta(days=1), status="Borrador", created_at=NOW,
    )
    data.update(kw)
    return Tender(**data)


def _expect_integrity(db, *objs):
    db.add_all(objs)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_oferta_unica_por_proveedor_y_licitacion(db):  # REQ-006 (BD)
    p, t = _provider(), _tender()
    db.add_all([p, t])
    db.flush()
    db.add(Offer(tender_id=t.id, provider_id=p.id, amount_cents=5_000, created_at=NOW))
    db.flush()
    _expect_integrity(db, Offer(tender_id=t.id, provider_id=p.id, amount_cents=4_000, created_at=NOW))


def test_oferta_monto_debe_ser_positivo(db):  # REQ-005 (BD)
    p, t = _provider(), _tender()
    db.add_all([p, t])
    db.flush()
    _expect_integrity(db, Offer(tender_id=t.id, provider_id=p.id, amount_cents=0, created_at=NOW))


def test_oferta_fk_inexistente(db):
    _expect_integrity(db, Offer(tender_id=999, provider_id=999, amount_cents=1, created_at=NOW))


def test_no_se_borra_proveedor_con_ofertas(db):  # FK activa, sin cascada
    p, t = _provider(), _tender()
    db.add_all([p, t])
    db.flush()
    db.add(Offer(tender_id=t.id, provider_id=p.id, amount_cents=1, created_at=NOW))
    db.flush()
    db.delete(p)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_name_key_unica(db):  # REQ-001 (BD)
    db.add(_provider("A", "a"))
    db.flush()
    _expect_integrity(db, _provider("a ", "a"))


def test_code_key_unica(db):  # REQ-002 (BD)
    db.add(_tender("LIC-1", "lic-1"))
    db.flush()
    _expect_integrity(db, _tender("lic-1", "lic-1"))


@pytest.mark.parametrize("kw", [{"budget_cents": 0}, {"budget_cents": -1}, {"status": "Abierta"}, {"title": "   "}])
def test_licitacion_checks(db, kw):
    _expect_integrity(db, _tender(**kw))


def test_tasa_debe_ser_positiva_y_fuente_valida(db):
    _expect_integrity(db, ExchangeRate(rate_x10000=0, rate_date=NOW.date(), source="manual", created_at=NOW))
    _expect_integrity(db, ExchangeRate(rate_x10000=5_000_000, rate_date=NOW.date(), source="otra", created_at=NOW))


@pytest.mark.parametrize(
    "kw",
    [
        dict(level="Gerencia", min_cents=0, max_cents=10),  # min >= 1
        dict(level="Gerencia", min_cents=10, max_cents=10),  # max > min
        dict(level="Otro", min_cents=1, max_cents=None),  # nivel válido
    ],
)
def test_rango_checks(db, kw):
    _expect_integrity(db, ApprovalRange(**kw))


def test_rango_nivel_unico(db):
    db.add(ApprovalRange(level="Gerencia", min_cents=1, max_cents=None))
    db.flush()
    _expect_integrity(db, ApprovalRange(level="Gerencia", min_cents=5, max_cents=None))


def test_usuario_username_unico_sin_distinguir_mayusculas_y_rol_valido(db):
    db.add(User(username="Admin", password_hash="x", role="admin"))
    db.flush()
    _expect_integrity(db, User(username="admin", password_hash="x", role="admin"))
    _expect_integrity(db, User(username="otro", password_hash="x", role="superuser"))


def test_fechas_se_leen_aware_utc(db):
    t = _tender()
    db.add(t)
    db.commit()
    db.expire_all()
    leido = db.get(Tender, t.id)
    assert leido.closes_at == NOW + timedelta(days=1)
    assert leido.closes_at.tzinfo is not None


def test_datetime_naive_rechazado(db):
    db.add(_tender(closes_at=datetime(2026, 12, 1)))
    with pytest.raises((ValueError, StatementError)):
        db.flush()
    db.rollback()
