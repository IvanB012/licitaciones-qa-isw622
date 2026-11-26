from datetime import timedelta

from sqlalchemy import func, select

from app.models import ApprovalRange, ExchangeRate, Offer, Provider, Tender, User
from seeds import seed as seed_module
from seeds.seed import reset_and_seed


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_seed_deja_estado_de_referencia(db, clock, seeded):
    assert _count(db, User) == 2
    assert _count(db, Provider) == 2
    assert _count(db, Offer) == 2
    rate = db.scalar(select(ExchangeRate))
    assert (rate.rate_x10000, rate.source) == (5_000_000, "seed")
    ranges = {r.level: (r.min_cents, r.max_cents) for r in db.scalars(select(ApprovalRange))}
    assert ranges == {
        "Encargado de área": (1, 100_000_000),
        "Gerencia": (100_000_000, 1_000_000_000),
        "Junta Directiva": (1_000_000_000, None),
    }
    l1 = db.get(Tender, seeded.tender_id)
    assert (l1.code, l1.status, l1.budget_cents) == ("LIC-2026-001", "Publicada", 1_000_000_000)
    assert l1.closes_at == clock.now() + timedelta(hours=48)
    montos = {db.get(Provider, o.provider_id).name: o.amount_cents for o in db.scalars(select(Offer))}
    assert montos == {"Tecnología Norte S.A.": 900_000_000, "Servicios del Valle": 950_000_000}


def test_seed_no_guarda_contrasenas_en_claro(db, seeded):
    hashes = [u.password_hash for u in db.scalars(select(User))]
    assert all(h.startswith("$argon2") for h in hashes)


def test_reset_es_reproducible(engine, db, clock):
    first = reset_and_seed(engine, clock)
    second = reset_and_seed(engine, clock)
    db.expire_all()
    assert (first.tender_id, first.p1_id) == (second.tender_id, second.p1_id)
    assert _count(db, User) == 2 and _count(db, Offer) == 2 and _count(db, Tender) == 1


def test_cli_reset_y_rechazo_sin_reset(settings, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    assert seed_module.main(["--reset"]) == 0
    assert seed_module.main(["--reset"]) == 0  # repetible
    assert seed_module.main([]) == 1  # ya hay datos
    assert "admin" in capsys.readouterr().out
