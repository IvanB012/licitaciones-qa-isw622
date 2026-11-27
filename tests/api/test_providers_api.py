"""API de proveedores (contrato §5). Esperado: REQ-001, REQ-011 y REQ-012 de CLAUDE.md."""
import unicodedata

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Provider
from app.rules.normalization import normalize_name
from tests.conftest import OPERADOR


@pytest.fixture
def op(client, seeded, login):
    """Sesión de operador y datos de referencia (P1 'Tecnología Norte S.A.' y P2 tienen ofertas en L1)."""
    assert login(*OPERADOR).status_code == 200
    return client


def _create(op, name="Insumos del Sur", **extra):
    return op.post("/api/providers", json={"name": name, **extra})


def _error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"] == code
    assert set(r.json()) == {"error", "detalle"}


# ---- crear (REQ-001) ----
def test_crear_proveedor_valido(op):  # REQ-001
    r = _create(op, contact_email="ventas@sur.cr")
    assert r.status_code == 201
    body = r.json()
    assert (body["name"], body["contact_email"]) == ("Insumos del Sur", "ventas@sur.cr")
    assert op.get(f"/api/providers/{body['id']}").json() == body


def test_crear_guarda_nombre_recortado_y_compactado(op):  # REQ-001
    assert _create(op, name="  Insumos   del   Sur ").json()["name"] == "Insumos del Sur"


@pytest.mark.parametrize("name", ["  tecnología   NORTE s.a. ", "TECNOLOGÍA NORTE S.A.", "Tecnología Norte S.A."])
def test_nombre_duplicado_equivalente_409(op, name):  # CP-001 / REQ-001
    _error(_create(op, name=name), 409, "duplicado")  # el seed ya tiene "Tecnología Norte S.A."


def test_duplicado_con_tilde_descompuesta_409(op):  # REQ-001
    descompuesto = unicodedata.normalize("NFD", "Tecnología Norte S.A.")
    assert descompuesto != "Tecnología Norte S.A."
    _error(_create(op, name=descompuesto), 409, "duplicado")


@pytest.mark.parametrize(
    "name",
    ["<script>alert(1)</script>", "Acme & Co", "Nombre; DROP TABLE", "", "   ", "Acme 😀", None, 42],
)
def test_nombre_invalido_422(op, name):  # CP-015 / REQ-012
    _error(_create(op, name=name), 422, "validacion_nombre")


def test_correo_invalido_422(op):  # REQ-001
    _error(_create(op, contact_email="no-es-correo"), 422, "validacion")


def test_cuerpo_sin_nombre_422_con_formato_de_error(op):  # REQ-011
    r = op.post("/api/providers", json={})
    _error(r, 422, "validacion")


def test_json_malformado_400(op):  # REQ-011
    r = op.post("/api/providers", content="{no es json", headers={"content-type": "application/json"})
    _error(r, 400, "solicitud_invalida")


def test_la_bd_tambien_rechaza_duplicado_y_responde_409(op, app, monkeypatch):  # REQ-001 / REQ-011
    # Simula una carrera: el chequeo previo no ve el duplicado, pero el UNIQUE de la BD sí.
    from app.services import providers as service

    monkeypatch.setattr(service, "_name_taken", lambda *a, **k: False)
    _error(_create(op, name="servicios DEL valle"), 409, "duplicado")


def test_bd_unique_name_key(db, seeded, clock):  # REQ-001
    db.add(Provider(name="x", name_key=normalize_name("Servicios del Valle"), created_at=clock.now()))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---- listar / obtener ----
def test_listar_incluye_seed_y_nuevo(op):  # REQ-001
    nuevo = _create(op).json()
    r = op.get("/api/providers")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert {"Tecnología Norte S.A.", "Servicios del Valle", "Insumos del Sur"} <= set(names)
    assert nuevo in r.json()


def test_obtener_inexistente_404(op):  # REQ-011
    _error(op.get("/api/providers/99999"), 404, "no_encontrado")


# ---- editar (REQ-001) ----
def test_editar_proveedor(op):  # REQ-001
    pid = _create(op).json()["id"]
    r = op.put(f"/api/providers/{pid}", json={"name": "Insumos del Norte (CR)", "contact_email": None})
    assert r.status_code == 200 and r.json()["name"] == "Insumos del Norte (CR)"


def test_editar_sin_falso_duplicado_contra_si_mismo(op, seeded):  # REQ-001
    pid = seeded.p1_id
    r = op.put(f"/api/providers/{pid}", json={"name": "  TECNOLOGÍA norte   s.a.  "})
    assert r.status_code == 200
    assert r.json()["name"] == "TECNOLOGÍA norte s.a."


def test_editar_a_nombre_de_otro_409(op, seeded):  # REQ-001
    _error(op.put(f"/api/providers/{seeded.p1_id}", json={"name": "servicios del valle"}), 409, "duplicado")


def test_editar_nombre_invalido_422_y_no_cambia(op, seeded):  # REQ-012
    _error(op.put(f"/api/providers/{seeded.p1_id}", json={"name": "<b>x</b>"}), 422, "validacion_nombre")
    assert op.get(f"/api/providers/{seeded.p1_id}").json()["name"] == "Tecnología Norte S.A."


def test_editar_inexistente_404(op):  # REQ-011
    _error(op.put("/api/providers/99999", json={"name": "Algo"}), 404, "no_encontrado")


# ---- borrar ----
def test_borrar_sin_ofertas_204(op):  # REQ-001
    pid = _create(op).json()["id"]
    assert op.delete(f"/api/providers/{pid}").status_code == 204
    _error(op.get(f"/api/providers/{pid}"), 404, "no_encontrado")


def test_borrar_con_ofertas_409_en_uso(op, seeded):  # REQ-001
    _error(op.delete(f"/api/providers/{seeded.p1_id}"), 409, "en_uso")
    assert op.get(f"/api/providers/{seeded.p1_id}").status_code == 200


def test_borrar_inexistente_404(op):  # REQ-011
    _error(op.delete("/api/providers/99999"), 404, "no_encontrado")


# ---- sesión y errores internos (REQ-011/012) ----
@pytest.mark.parametrize(
    "method, path",
    [("get", "/api/providers"), ("post", "/api/providers"), ("get", "/api/providers/1"),
     ("put", "/api/providers/1"), ("delete", "/api/providers/1")],
)
def test_sin_sesion_401(client, seeded, method, path):  # REQ-011
    r = getattr(client, method)(path, **({"json": {"name": "X"}} if method in ("post", "put") else {}))
    _error(r, 401, "no_autenticado")


def test_error_no_expone_trazas_ni_rutas(op):  # CP-016 / REQ-012
    texto = _create(op, name="<script>").text + op.get("/api/providers/99999").text
    for prohibido in ("Traceback", "File \"", ".py", "sqlalchemy", "sqlite"):
        assert prohibido not in texto
