"""Formato de errores del contrato §4 (REQ-011/REQ-012: sin trazas, rutas ni credenciales)."""
import pytest
from fastapi import Depends

from app.deps import require_admin
from app.errors import Conflict, ValidationFailed
from tests.conftest import OPERADOR

SECRETO = r"C:\Users\ivanv\secreto\db.py password=hunter2 Traceback"


@pytest.fixture
def boom_app(app):
    @app.get("/api/_boom")
    def boom():
        raise RuntimeError(SECRETO)

    @app.get("/_boom_ui")
    def boom_ui():
        raise RuntimeError(SECRETO)

    @app.get("/api/_conflict")
    def conflict():
        raise Conflict("Ya existe.", code="duplicado")

    @app.get("/api/_invalid")
    def invalid():
        raise ValidationFailed("Monto inválido.", code="monto_invalido")

    @app.get("/api/_admin")
    def admin_only(_=Depends(require_admin)):
        return {"ok": True}

    return app


def _assert_sin_fugas(text: str):
    for prohibido in ("hunter2", "Traceback", "RuntimeError", "secreto", "db.py", 'File "'):
        assert prohibido not in text


def test_500_api_formato_generico_sin_traza(boom_app, client):  # REQ-012
    r = client.get("/api/_boom")
    assert r.status_code == 500
    assert r.json()["error"] == "error_interno"
    assert set(r.json()) == {"error", "detalle"}
    _assert_sin_fugas(r.text)


def test_500_ui_pagina_generica_sin_traza(boom_app, client):  # REQ-012
    r = client.get("/_boom_ui")
    assert r.status_code == 500
    assert "text/html" in r.headers["content-type"]
    _assert_sin_fugas(r.text)


def test_404_api(client):
    r = client.get("/api/no-existe")
    assert r.status_code == 404 and r.json()["error"] == "no_encontrado"


def test_405_api(client):
    r = client.get("/api/auth/login")
    assert r.status_code == 405 and r.json()["error"] == "metodo_no_permitido"


def test_dominio_409_y_422(boom_app, client):
    r = client.get("/api/_conflict")
    assert (r.status_code, r.json()) == (409, {"error": "duplicado", "detalle": "Ya existe."})
    r = client.get("/api/_invalid")
    assert (r.status_code, r.json()["error"]) == (422, "monto_invalido")


def test_403_operador_en_ruta_admin(boom_app, client, seeded, login):
    assert client.get("/api/_admin").status_code == 401
    login(*OPERADOR)
    r = client.get("/api/_admin")
    assert r.status_code == 403 and r.json()["error"] == "prohibido"


def test_validacion_no_eco_de_valores(client):
    r = client.post("/api/auth/login", json={"username": "u", "password": ["secreta-123"]})
    assert r.status_code == 422
    assert "secreta-123" not in r.text
