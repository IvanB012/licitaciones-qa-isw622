"""Fixtures compartidas: BD temporal limpia por prueba, FakeClock, proveedor de cambio que falla, cliente y seed."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.clock import FakeClock
from app.config import Settings
from app.db import create_tables, make_engine, make_session_factory
from app.exchange import FailingExchangeRateProvider
from app.main import create_app
from seeds.seed import SEED_USERS, seed_reference_data

ADMIN = (SEED_USERS[0][0], SEED_USERS[0][1])
OPERADOR = (SEED_USERS[1][0], SEED_USERS[1][1])


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", secret_key="clave-de-prueba", env="test")


@pytest.fixture
def engine(settings):
    eng = make_engine(settings.database_url)
    create_tables(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def rate_provider() -> FailingExchangeRateProvider:
    return FailingExchangeRateProvider()  # las pruebas nunca tocan la red


@pytest.fixture
def app(settings, engine, clock, rate_provider):
    return create_app(settings=settings, engine=engine, clock=clock, rate_provider=rate_provider)


@pytest.fixture
def client(app):
    # raise_server_exceptions=False: los errores no controlados llegan como respuesta 500, como en producción
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def db(engine):
    with make_session_factory(engine)() as session:
        yield session


@pytest.fixture
def seeded(db, clock):
    return seed_reference_data(db, clock)


@pytest.fixture
def login(client):
    """login(usuario, clave) -> respuesta de POST /api/auth/login (deja la cookie en el cliente)."""

    def _login(username: str, password: str):
        return client.post("/api/auth/login", json={"username": username, "password": password})

    return _login
