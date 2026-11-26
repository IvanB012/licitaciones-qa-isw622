"""API de ofertas (contrato §5). Esperado: REQ-004, REQ-005, REQ-006 y REQ-011 de CLAUDE.md."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import create_app
from app.models import Offer, Provider
from app.rules.normalization import normalize_name
from tests.conftest import OPERADOR

# El FakeClock arranca el 2026-11-26 12:00Z; L1 (seed) cierra 48 h después.
CIERRE_L1 = "2026-11-28T12:00:00Z"
CIERRE_NUEVA = "2026-11-28T18:00:00Z"


@pytest.fixture
def op(client, seeded, login):
    assert login(*OPERADOR).status_code == 200
    return client


@pytest.fixture
def p3(db, clock):
    """Tercer proveedor sintético sin ofertas (P1 y P2 ya ofertaron en L1)."""
    p = Provider(name="Soluciones Pacífico", name_key=normalize_name("Soluciones Pacífico"), created_at=clock.now())
    db.add(p)
    db.commit()
    return p


@pytest.fixture
def aislada(op):
    """Licitación nueva, Publicada, presupuesto CRC 1 000 000,00 y sin ofertas (escenario de fronteras del enunciado)."""
    body = {"code": "LIC-AISLADA", "title": "Escenario aislado", "budget": "1000000.00", "closes_at": CIERRE_NUEVA}
    tender = op.post("/api/tenders", json=body).json()
    assert op.post(f"/api/tenders/{tender['id']}/publish").status_code == 200
    return tender


def _offer(op, tender_id, provider_id, amount):
    return op.post(f"/api/tenders/{tender_id}/offers", json={"provider_id": provider_id, "amount": amount})


def _error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"] == code
    assert set(r.json()) == {"error", "detalle"}


# ---- crear: caso feliz (REQ-005) ----
def test_crear_oferta_valida(op, seeded, p3, clock):  # REQ-005
    r = _offer(op, seeded.tender_id, p3.id, "9800000.00")
    assert r.status_code == 201
    body = r.json()
    assert (body["tender_id"], body["provider_id"], body["amount"]) == (seeded.tender_id, p3.id, "9800000.00")
    assert body["created_at"] == "2026-11-26T12:00:00Z"  # sale del Clock inyectado
    assert op.get(f"/api/offers/{body['id']}").json() == body


# ---- montos y fronteras (REQ-005) ----
def test_oferta_igual_al_presupuesto_es_valida(op, aislada, seeded):  # REQ-005
    assert _offer(op, aislada["id"], seeded.p1_id, "1000000.00").status_code == 201


def test_oferta_un_centimo_sobre_el_presupuesto_422(op, aislada, seeded):  # REQ-005
    _error(_offer(op, aislada["id"], seeded.p1_id, "1000000.01"), 422, "monto_excede_presupuesto")


@pytest.mark.parametrize("monto", ["900000.00", "950000.00", "0.01"])
def test_ofertas_validas_bajo_el_presupuesto(op, aislada, seeded, monto):  # REQ-005
    assert _offer(op, aislada["id"], seeded.p1_id, monto).status_code == 201


@pytest.mark.parametrize("monto", ["0", "0.00", "-1", "-900000.00", "abc", "", "1e3", "1,5", "10.001"])
def test_oferta_cero_negativa_o_invalida_422(op, aislada, seeded, monto):  # REQ-005 / REQ-011
    _error(_offer(op, aislada["id"], seeded.p1_id, monto), 422, "monto_invalido")


@pytest.mark.parametrize("monto", [900000, 900000.5, None, True])
def test_monto_que_no_es_texto_422(op, aislada, seeded, monto):  # REQ-011: el dinero solo viaja como string
    _error(_offer(op, aislada["id"], seeded.p1_id, monto), 422, "monto_invalido")


def test_provider_id_no_numerico_422(op, aislada):
    r = op.post(f"/api/tenders/{aislada['id']}/offers", json={"provider_id": "abc", "amount": "1.00"})
    assert r.status_code == 422 and r.json()["error"] == "validacion"


def test_cuerpo_incompleto_422(op, aislada):
    assert op.post(f"/api/tenders/{aislada['id']}/offers", json={"provider_id": 1}).status_code == 422


# ---- plazo (REQ-004): antes / exactamente / después ----
def test_un_segundo_antes_del_cierre_se_acepta(op, seeded, p3, clock):  # REQ-004
    clock.set(clock.now() + timedelta(hours=48) - timedelta(seconds=1))
    assert _offer(op, seeded.tender_id, p3.id, "9000000.00").status_code == 201


def test_exactamente_en_el_cierre_se_rechaza(op, seeded, p3, clock):  # REQ-004
    clock.set(clock.now() + timedelta(hours=48))  # == closes_at
    _error(_offer(op, seeded.tender_id, p3.id, "9000000.00"), 409, "licitacion_vencida")


def test_un_segundo_despues_del_cierre_se_rechaza(op, seeded, p3, clock):  # REQ-004
    clock.set(clock.now() + timedelta(hours=48, seconds=1))
    _error(_offer(op, seeded.tender_id, p3.id, "9000000.00"), 409, "licitacion_vencida")


def test_oferta_rechazada_por_plazo_no_se_guarda(op, seeded, p3, clock, db):  # REQ-004
    antes = db.scalar(select(func.count()).select_from(Offer))
    clock.set(clock.now() + timedelta(days=3))
    _offer(op, seeded.tender_id, p3.id, "9000000.00")
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Offer)) == antes


# ---- estado de la licitación (REQ-004) ----
def _borrador(op):
    body = {"code": "LIC-BORR", "title": "En borrador", "budget": "1000000.00", "closes_at": CIERRE_NUEVA}
    return op.post("/api/tenders", json=body).json()


def test_licitacion_en_borrador_no_acepta_ofertas(op, seeded):  # REQ-004
    t = _borrador(op)
    _error(_offer(op, t["id"], seeded.p1_id, "500000.00"), 409, "licitacion_no_publicada")


def test_licitacion_cerrada_no_acepta_ofertas(op, seeded, p3):  # REQ-004
    op.post(f"/api/tenders/{seeded.tender_id}/close")
    _error(_offer(op, seeded.tender_id, p3.id, "9000000.00"), 409, "licitacion_no_publicada")


# ---- existencia (404) y orden de validación del contrato ----
def test_licitacion_inexistente_404(op, seeded):
    _error(_offer(op, 9999, seeded.p1_id, "1.00"), 404, "no_encontrado")


def test_proveedor_inexistente_404(op, aislada):
    _error(_offer(op, aislada["id"], 9999, "1.00"), 404, "no_encontrado")


def test_orden_licitacion_antes_que_proveedor(op):
    _error(_offer(op, 9999, 9999, "abc"), 404, "no_encontrado")


def test_orden_estado_antes_que_monto(op, seeded):  # contrato §5
    t = _borrador(op)
    _error(_offer(op, t["id"], seeded.p1_id, "-5"), 409, "licitacion_no_publicada")


def test_orden_vencimiento_antes_que_monto(op, seeded, p3, clock):  # contrato §5
    clock.set(clock.now() + timedelta(days=3))
    _error(_offer(op, seeded.tender_id, p3.id, "99999999999.00"), 409, "licitacion_vencida")


def test_orden_monto_antes_que_duplicado(op, seeded):  # contrato §5
    _error(_offer(op, seeded.tender_id, seeded.p1_id, "99999999.00"), 422, "monto_excede_presupuesto")


# ---- duplicados (REQ-006) ----
def test_proveedor_no_puede_ofertar_dos_veces(op, seeded):  # REQ-006
    _error(_offer(op, seeded.tender_id, seeded.p1_id, "8000000.00"), 409, "oferta_duplicada")


def test_el_duplicado_no_altera_la_oferta_original(op, seeded):  # REQ-006
    _offer(op, seeded.tender_id, seeded.p1_id, "1.00")
    assert op.get(f"/api/offers/{seeded.offer_p1_id}").json()["amount"] == "9000000.00"


def test_mismo_proveedor_puede_ofertar_en_otra_licitacion(op, aislada, seeded):  # REQ-006: único por licitación
    assert _offer(op, aislada["id"], seeded.p1_id, "900000.00").status_code == 201


def test_la_bd_tambien_rechaza_el_duplicado(op, seeded, monkeypatch):  # REQ-006 (UNIQUE como segunda barrera)
    from app.services import offers as service

    monkeypatch.setattr(service, "_offer_exists", lambda *a, **k: False)  # se salta el chequeo del service
    _error(_offer(op, seeded.tender_id, seeded.p1_id, "8000000.00"), 409, "oferta_duplicada")


# ---- consultar ----
def test_listar_ofertas_de_la_licitacion_en_orden_de_registro(op, seeded, p3, clock):
    clock.advance(seconds=5)
    nueva = _offer(op, seeded.tender_id, p3.id, "9800000.00").json()
    lista = op.get(f"/api/tenders/{seeded.tender_id}/offers").json()
    assert [o["id"] for o in lista] == [seeded.offer_p1_id, seeded.offer_p2_id, nueva["id"]]
    assert [o["amount"] for o in lista] == ["9000000.00", "9500000.00", "9800000.00"]


def test_listar_ofertas_de_licitacion_sin_ofertas(op, aislada):
    assert op.get(f"/api/tenders/{aislada['id']}/offers").json() == []


def test_listar_de_licitacion_inexistente_404(op):
    _error(op.get("/api/tenders/9999/offers"), 404, "no_encontrado")


def test_obtener_oferta_inexistente_404(op):
    _error(op.get("/api/offers/9999"), 404, "no_encontrado")


def test_rutas_exigen_sesion(client, seeded):  # REQ-011
    for r in (
        client.get(f"/api/tenders/{seeded.tender_id}/offers"),
        client.post(f"/api/tenders/{seeded.tender_id}/offers", json={"provider_id": 1, "amount": "1.00"}),
        client.get(f"/api/offers/{seeded.offer_p1_id}"),
        client.put(f"/api/offers/{seeded.offer_p1_id}", json={"amount": "1.00"}),
        client.delete(f"/api/offers/{seeded.offer_p1_id}"),
    ):
        _error(r, 401, "no_autenticado")


# ---- editar ----
def test_editar_monto_no_cambia_el_orden_de_registro(op, seeded, db):  # REQ-007 (desempate usa created_at)
    antes = op.get(f"/api/offers/{seeded.offer_p2_id}").json()
    r = op.put(f"/api/offers/{seeded.offer_p2_id}", json={"amount": "8500000.00"})
    assert r.status_code == 200
    assert r.json()["amount"] == "8500000.00" and r.json()["created_at"] == antes["created_at"]


def test_editar_aplica_las_mismas_reglas_de_monto(op, seeded):  # REQ-005 / REQ-011
    url = f"/api/offers/{seeded.offer_p1_id}"
    _error(op.put(url, json={"amount": "10000000.01"}), 422, "monto_excede_presupuesto")
    _error(op.put(url, json={"amount": "0"}), 422, "monto_invalido")
    _error(op.put(url, json={"amount": 5}), 422, "monto_invalido")
    assert op.put(url, json={"amount": "10000000.00"}).status_code == 200  # igual al presupuesto


def test_editar_exactamente_en_el_cierre_409(op, seeded, clock):  # REQ-004
    clock.set(clock.now() + timedelta(hours=48))
    _error(op.put(f"/api/offers/{seeded.offer_p1_id}", json={"amount": "8000000.00"}), 409, "licitacion_vencida")


def test_editar_en_licitacion_cerrada_409(op, seeded):  # REQ-004
    op.post(f"/api/tenders/{seeded.tender_id}/close")
    _error(op.put(f"/api/offers/{seeded.offer_p1_id}", json={"amount": "8000000.00"}), 409, "licitacion_no_publicada")


def test_editar_inexistente_404(op):
    _error(op.put("/api/offers/9999", json={"amount": "1.00"}), 404, "no_encontrado")


# ---- borrar ----
def test_borrar_oferta_con_licitacion_abierta_204(op, seeded):
    assert op.delete(f"/api/offers/{seeded.offer_p2_id}").status_code == 204
    _error(op.get(f"/api/offers/{seeded.offer_p2_id}"), 404, "no_encontrado")
    assert len(op.get(f"/api/tenders/{seeded.tender_id}/offers").json()) == 1


def test_borrar_y_volver_a_ofertar(op, seeded):  # REQ-006: al borrar queda libre el par licitación-proveedor
    op.delete(f"/api/offers/{seeded.offer_p1_id}")
    assert _offer(op, seeded.tender_id, seeded.p1_id, "9100000.00").status_code == 201


def test_borrar_vencida_409(op, seeded, clock):  # REQ-004
    clock.set(clock.now() + timedelta(hours=48))
    _error(op.delete(f"/api/offers/{seeded.offer_p1_id}"), 409, "licitacion_vencida")


def test_borrar_en_licitacion_cerrada_409(op, seeded):
    op.post(f"/api/tenders/{seeded.tender_id}/close")
    _error(op.delete(f"/api/offers/{seeded.offer_p1_id}"), 409, "licitacion_no_publicada")


def test_borrar_inexistente_404(op):
    _error(op.delete("/api/offers/9999"), 404, "no_encontrado")


# ---- persistencia (REQ-011) ----
def test_las_ofertas_persisten_al_reiniciar_la_app(op, seeded, p3, settings, clock, rate_provider):  # REQ-011
    creada = _offer(op, seeded.tender_id, p3.id, "9800000.00").json()
    reiniciada = create_app(settings=settings, clock=clock, rate_provider=rate_provider)  # motor nuevo, misma BD
    with TestClient(reiniciada, raise_server_exceptions=False) as c:
        c.post("/api/auth/login", json={"username": OPERADOR[0], "password": OPERADOR[1]})
        assert c.get(f"/api/offers/{creada['id']}").json() == creada
        assert len(c.get(f"/api/tenders/{seeded.tender_id}/offers").json()) == 3
