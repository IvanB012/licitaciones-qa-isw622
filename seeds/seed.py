"""Seed de referencia reproducible.

    python -m seeds.seed --reset      # borra todo y deja la BD en el estado de referencia

Reutilizable en tests:  seed_reference_data(session, clock)  /  reset_and_seed(engine, clock)
Todos los usuarios y datos son SINTÉTICOS.
"""
import argparse
import sys
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.clock import Clock, SystemClock
from app.config import get_settings
from app.db import create_tables, drop_tables, make_engine, make_session_factory
from app.models import ApprovalRange, ExchangeRate, Offer, Provider, Tender, User
from app.rules.constants import (
    LEVEL_ENCARGADO,
    LEVEL_GERENCIA,
    LEVEL_JUNTA,
    RATE_SOURCE_SEED,
    ROLE_ADMIN,
    ROLE_OPERADOR,
    STATUS_PUBLICADA,
)
from app.rules.normalization import compact_spaces, normalize_code, normalize_name
from app.rules.timeutil import official_date
from app.security import hash_password

# (username, contraseña de prueba, rol) — contrato §8
SEED_USERS = (
    ("admin", "Admin#2026-test", ROLE_ADMIN),
    ("operador", "Operador#2026-test", ROLE_OPERADOR),
)
# (nivel, min_cents inclusivo, max_cents exclusivo) — contrato §6
SEED_RANGES = (
    (LEVEL_ENCARGADO, 1, 100_000_000),
    (LEVEL_GERENCIA, 100_000_000, 1_000_000_000),
    (LEVEL_JUNTA, 1_000_000_000, None),
)
SEED_RATE_X10000 = 5_000_000  # CRC 500,00 por USD
P1_NAME = "Tecnología Norte S.A."
P2_NAME = "Servicios del Valle"
L1_CODE = "LIC-2026-001"
L1_BUDGET_CENTS = 1_000_000_000  # CRC 10 000 000,00
P1_OFFER_CENTS = 900_000_000  # CRC 9 000 000,00
P2_OFFER_CENTS = 950_000_000  # CRC 9 500 000,00


@dataclass
class SeedResult:
    admin_id: int
    operador_id: int
    p1_id: int
    p2_id: int
    tender_id: int
    offer_p1_id: int
    offer_p2_id: int
    exchange_rate_id: int


def seed_reference_data(session: Session, clock: Clock) -> SeedResult:
    """Inserta los datos de referencia directamente por los modelos (la BD debe estar vacía)."""
    now = clock.now()

    users = [
        User(username=u, password_hash=hash_password(p), role=r, active=True) for u, p, r in SEED_USERS
    ]
    session.add_all(users)
    session.add_all(ApprovalRange(level=lv, min_cents=lo, max_cents=hi) for lv, lo, hi in SEED_RANGES)
    rate = ExchangeRate(
        rate_x10000=SEED_RATE_X10000, rate_date=official_date(now), source=RATE_SOURCE_SEED, created_at=now
    )
    session.add(rate)

    p1 = Provider(name=compact_spaces(P1_NAME), name_key=normalize_name(P1_NAME), created_at=now)
    p2 = Provider(name=compact_spaces(P2_NAME), name_key=normalize_name(P2_NAME), created_at=now)
    l1 = Tender(
        code=L1_CODE,
        code_key=normalize_code(L1_CODE),
        title="Compra de equipo de cómputo",
        description="Licitación de referencia del seed.",
        budget_cents=L1_BUDGET_CENTS,
        closes_at=now + timedelta(hours=48),
        status=STATUS_PUBLICADA,
        created_at=now,
    )
    session.add_all([p1, p2, l1])
    session.flush()  # obtiene los ids

    # P2 un segundo después: el orden de registro queda determinista (desempate REQ-007)
    o1 = Offer(tender_id=l1.id, provider_id=p1.id, amount_cents=P1_OFFER_CENTS, created_at=now)
    o2 = Offer(
        tender_id=l1.id, provider_id=p2.id, amount_cents=P2_OFFER_CENTS, created_at=now + timedelta(seconds=1)
    )
    session.add_all([o1, o2])
    session.commit()
    return SeedResult(
        admin_id=users[0].id,
        operador_id=users[1].id,
        p1_id=p1.id,
        p2_id=p2.id,
        tender_id=l1.id,
        offer_p1_id=o1.id,
        offer_p2_id=o2.id,
        exchange_rate_id=rate.id,
    )


def reset_and_seed(engine: Engine, clock: Clock | None = None) -> SeedResult:
    """Borra todas las tablas, las recrea y siembra. Deja la BD en el estado de referencia."""
    drop_tables(engine)
    create_tables(engine)
    with make_session_factory(engine)() as session:
        return seed_reference_data(session, clock or SystemClock())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siembra la BD con los datos de referencia (sintéticos).")
    parser.add_argument("--reset", action="store_true", help="borra todo y vuelve al estado de referencia")
    args = parser.parse_args(argv)

    engine = make_engine(get_settings().database_url)
    try:
        if args.reset:
            reset_and_seed(engine)
        else:
            create_tables(engine)
            with make_session_factory(engine)() as session:
                if session.scalar(select(func.count()).select_from(User)):
                    print("La BD ya tiene datos. Use --reset para reiniciarla.", file=sys.stderr)
                    return 1
                seed_reference_data(session, SystemClock())
    finally:
        engine.dispose()
    print("Seed listo. Usuarios de prueba (sintéticos):")
    for username, password, role in SEED_USERS:
        print(f"  {username} / {password}  ({role})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
