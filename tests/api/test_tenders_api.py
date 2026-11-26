"""API de licitaciones (contrato §5). Esperado: REQ-002, REQ-003, REQ-011 y REQ-012 de CLAUDE.md."""
from datetime import timedelta

import pytest

from app.main import create_app
from app.models import Offer
from tests.conftest import OPERADOR

CIERRE = "2026-11-28T18:00:00Z"  # el FakeClock arranca el 2026-11-26 12:00Z
BODY = {"code": "LIC-2026-050", "title": "Compra de mobiliario", "budget": "1000000.00", "closes_at": CIERRE}


@pytest.fixture
def op(client, seeded, login):
    """Cliente con sesión de operador y datos de referencia (L1 = LIC-2026-001, Publicada, con 2 ofertas)."""
    assert login(*OPERADOR).status_code == 200
    return client


def _create(op, **over):
    return op.post("/api/tenders", json={**BODY, **over})


def _error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"] == code
    assert set(r.json()) == {"error", "detalle"}


# ---- crear (REQ-002) ----
def test_crear_licitacion_valida(op):  # REQ-002
    r = _create(op, description="Sillas y escritorios")
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "Borrador"
    assert (body["code"], body["title"], body["budget"], body["closes_at"]) == (
        "LIC-2026-050", "Compra de mobiliario", "1000000.00", CIERRE,
    )
    assert body["description"] == "Sillas y escritorios"
    assert op.get(f"/api/tenders/{body['id']}").json() == body


def test_crear_recorta_codigo_y_titulo(op):  # REQ-002
    body = _create(op, code="  LIC-X  ", title="  Algo  ").json()
    assert (body["code"], body["title"]) == ("LIC-X", "Algo")


@pytest.mark.parametrize("code", ["lic-2026-001", "  LIC-2026-001  ", "Lic-2026-001"])
def test_codigo_duplicado_sin_distinguir_mayusculas_ni_espacios(op, code):  # REQ-002
    _error(_create(op, code=code), 409, "duplicado")  # el seed ya tiene LIC-2026-001


def test_codigo_vacio_422(op):  # REQ-002
    _error(_create(op, code="   "), 422, "validacion_codigo")


@pytest.mark.parametrize("title", ["", "   "])
def test_titulo_vacio_422(op, title):  # REQ-002
    _error(_create(op, title=title), 422, "validacion_titulo")


@pytest.mark.parametrize("budget", ["0", "0.00", "-5", "abc", "1e3", "1,5", "10.001", ""])
def test_presupuesto_cero_negativo_o_invalido_422(op, budget):  # REQ-002 / REQ-011
    _error(_create(op, budget=budget), 422, "monto_invalido")


@pytest.mark.parametrize("budget", [1000000, 1000000.5, None])
def test_presupuesto_no_texto_422(op, budget):  # REQ-011: el dinero solo viaja como string
    assert _create(op, budget=budget).status_code == 422


def test_cierre_pasado_422(op):  # REQ-002
    _error(_create(op, closes_at="2026-11-26T11:59:59Z"), 422, "cierre_no_futuro")


def test_cierre_exactamente_ahora_422(op):  # REQ-002 (límite)
    _error(_create(op, closes_at="2026-11-26T12:00:00Z"), 422, "cierre_no_futuro")


def test_cierre_un_segundo_despues_201(op):  # REQ-002 (límite)
    assert _create(op, closes_at="2026-11-26T12:00:01Z").status_code == 201


def test_cierre_sin_zona_horaria_422(op):
    assert _create(op, closes_at="2026-11-28T18:00:00").status_code == 422


def test_campos_obligatorios_faltantes_422(op):
    r = op.post("/api/tenders", json={"code": "X"})
    assert r.status_code == 422 and r.json()["error"] == "validacion"


def test_titulo_con_script_se_guarda_como_texto_y_no_se_ejecuta(op):  # REQ-012
    r = _create(op, title="<script>alert(1)</script>")
    assert r.status_code == 201 and r.json()["title"] == "<script>alert(1)</script>"  # la API devuelve JSON, no HTML


# ---- consultar ----
def test_listar_y_filtrar_por_estado(op, seeded):  # REQ-011
    nuevo = _create(op).json()
    todos = op.get("/api/tenders").json()
    assert {t["id"] for t in todos} == {seeded.tender_id, nuevo["id"]}
    publicadas = op.get("/api/tenders", params={"status": "Publicada"}).json()
    assert [t["id"] for t in publicadas] == [seeded.tender_id]
    assert [t["id"] for t in op.get("/api/tenders", params={"status": "Borrador"}).json()] == [nuevo["id"]]


def test_filtro_de_estado_invalido_422(op):
    _error(op.get("/api/tenders", params={"status": "Abierta"}), 422, "validacion")


def test_obtener_inexistente_404(op):
    _error(op.get("/api/tenders/9999"), 404, "no_encontrado")


def test_sin_sesion_401(client, seeded):  # REQ-011
    _error(client.get("/api/tenders"), 401, "no_autenticado")
    _error(client.post("/api/tenders", json=BODY), 401, "no_autenticado")


# ---- editar ----
def test_editar_en_borrador(op):  # REQ-002
    t = _create(op).json()
    r = op.put(f"/api/tenders/{t['id']}", json={**BODY, "title": "Nuevo título", "budget": "2500000.50"})
    assert r.status_code == 200
    assert (r.json()["title"], r.json()["budget"], r.json()["status"]) == ("Nuevo título", "2500000.50", "Borrador")


def test_editar_conservando_su_propio_codigo(op):  # el duplicado ignora a sí misma
    t = _create(op).json()
    assert op.put(f"/api/tenders/{t['id']}", json={**BODY, "code": "lic-2026-050"}).status_code == 200


def test_editar_con_codigo_de_otra_409(op):  # REQ-002
    t = _create(op).json()
    _error(op.put(f"/api/tenders/{t['id']}", json={**BODY, "code": " lic-2026-001 "}), 409, "duplicado")


def test_editar_aplica_las_mismas_validaciones(op):  # REQ-011
    t = _create(op).json()
    _error(op.put(f"/api/tenders/{t['id']}", json={**BODY, "budget": "0"}), 422, "monto_invalido")
    _error(op.put(f"/api/tenders/{t['id']}", json={**BODY, "title": " "}), 422, "validacion_titulo")


def test_editar_publicada_409(op, seeded):  # contrato §5: solo Borrador
    _error(op.put(f"/api/tenders/{seeded.tender_id}", json=BODY), 409, "transicion_invalida")


def test_editar_inexistente_404(op):
    _error(op.put("/api/tenders/9999", json=BODY), 404, "no_encontrado")


# ---- borrar ----
def test_borrar_borrador_sin_ofertas_204(op):
    t = _create(op).json()
    assert op.delete(f"/api/tenders/{t['id']}").status_code == 204
    _error(op.get(f"/api/tenders/{t['id']}"), 404, "no_encontrado")


def test_borrar_publicada_409_en_uso(op, seeded):
    _error(op.delete(f"/api/tenders/{seeded.tender_id}"), 409, "en_uso")


def test_borrar_borrador_con_ofertas_409_en_uso(op, seeded, db, clock):
    t = _create(op).json()
    db.add(Offer(tender_id=t["id"], provider_id=seeded.p1_id, amount_cents=100, created_at=clock.now()))
    db.commit()
    _error(op.delete(f"/api/tenders/{t['id']}"), 409, "en_uso")


def test_borrar_inexistente_404(op):
    _error(op.delete("/api/tenders/9999"), 404, "no_encontrado")


# ---- estados (REQ-003) ----
def test_publicar_borrador(op):  # REQ-003
    t = _create(op).json()
    r = op.post(f"/api/tenders/{t['id']}/publish")
    assert r.status_code == 200 and r.json()["status"] == "Publicada"


def test_publicar_dos_veces_409(op):  # REQ-003
    t = _create(op).json()
    op.post(f"/api/tenders/{t['id']}/publish")
    _error(op.post(f"/api/tenders/{t['id']}/publish"), 409, "transicion_invalida")


def test_publicar_con_cierre_ya_vencido_422(op, clock):  # REQ-002 (al publicar)
    t = _create(op).json()
    clock.set(clock.now() + timedelta(days=5))  # pasa la fecha de cierre
    _error(op.post(f"/api/tenders/{t['id']}/publish"), 422, "cierre_no_futuro")
    assert op.get(f"/api/tenders/{t['id']}").json()["status"] == "Borrador"


def test_publicar_exactamente_en_el_cierre_422(op, clock):  # REQ-002 (límite)
    t = _create(op).json()
    clock.set(clock.now().replace(year=2026, month=11, day=28, hour=18))  # == closes_at
    _error(op.post(f"/api/tenders/{t['id']}/publish"), 422, "cierre_no_futuro")


def test_cerrar_publicada(op, seeded):  # REQ-003
    r = op.post(f"/api/tenders/{seeded.tender_id}/close")
    assert r.status_code == 200 and r.json()["status"] == "Cerrada"


def test_cerrar_borrador_directo(op):  # REQ-003: Borrador -> Cerrada permitido
    t = _create(op).json()
    assert op.post(f"/api/tenders/{t['id']}/close").json()["status"] == "Cerrada"


def test_cerrar_cerrada_409(op, seeded):  # REQ-003
    op.post(f"/api/tenders/{seeded.tender_id}/close")
    _error(op.post(f"/api/tenders/{seeded.tender_id}/close"), 409, "transicion_invalida")


def test_no_se_reabre_una_cerrada_409(op, seeded):  # REQ-003
    op.post(f"/api/tenders/{seeded.tender_id}/close")
    _error(op.post(f"/api/tenders/{seeded.tender_id}/publish"), 409, "transicion_invalida")


def test_cerrada_no_se_puede_editar_ni_borrar(op, seeded):  # REQ-003
    op.post(f"/api/tenders/{seeded.tender_id}/close")
    _error(op.put(f"/api/tenders/{seeded.tender_id}", json=BODY), 409, "transicion_invalida")
    _error(op.delete(f"/api/tenders/{seeded.tender_id}"), 409, "en_uso")


def test_publicar_y_cerrar_inexistente_404(op):
    _error(op.post("/api/tenders/9999/publish"), 404, "no_encontrado")
    _error(op.post("/api/tenders/9999/close"), 404, "no_encontrado")


# ---- persistencia (REQ-011) ----
def test_los_datos_persisten_al_reiniciar_la_app(op, settings, clock, rate_provider):  # REQ-011
    from fastapi.testclient import TestClient

    creada = _create(op).json()
    op.post(f"/api/tenders/{creada['id']}/publish")

    reiniciada = create_app(settings=settings, clock=clock, rate_provider=rate_provider)  # motor nuevo, misma BD
    with TestClient(reiniciada, raise_server_exceptions=False) as c:
        c.post("/api/auth/login", json={"username": OPERADOR[0], "password": OPERADOR[1]})
        r = c.get(f"/api/tenders/{creada['id']}")
    assert r.status_code == 200
    assert r.json()["status"] == "Publicada" and r.json()["budget"] == "1000000.00"
