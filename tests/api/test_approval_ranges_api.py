"""API de rangos de aprobación (contrato §5, §6). Esperado: REQ-009 y REQ-011 de CLAUDE.md."""
import pytest

from app.models import ApprovalRange
from tests.conftest import ADMIN, OPERADOR

E, G, J = "Encargado de área", "Gerencia", "Junta Directiva"


@pytest.fixture
def adm(client, seeded, login):
    """Sesión de admin sobre los datos de referencia (3 rangos del seed)."""
    assert login(*ADMIN).status_code == 200
    return client


@pytest.fixture
def vacio(adm, db):
    """Admin sin rangos guardados, para armar escenarios de traslape desde cero."""
    db.query(ApprovalRange).delete()
    db.commit()
    return adm


def _error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"] == code
    assert set(r.json()) == {"error", "detalle"}


def _post(c, level, lo, hi=None):
    return c.post("/api/approval-ranges", json={"level": level, "min": lo, "max": hi})


# ---- listar / seed ----
def test_listar_devuelve_los_tres_rangos_del_seed_ordenados_por_min(adm):  # CP-### / REQ-009
    body = adm.get("/api/approval-ranges").json()
    assert [(r["level"], r["min"], r["max"]) for r in body] == [
        (E, "0.01", "1000000.00"), (G, "1000000.00", "10000000.00"), (J, "10000000.00", None),
    ]


def test_rangos_del_seed_no_se_traslapan_entre_si(adm):  # CP-### / REQ-009
    body = adm.get("/api/approval-ranges").json()
    for r in body:
        r_id = r["id"]
        # re-guardar cada rango del seed tal cual NO choca con los demás (ni consigo mismo)
        assert adm.put(f"/api/approval-ranges/{r_id}", json={"level": r["level"], "min": r["min"], "max": r["max"]}).status_code == 200


# ---- crear ----
def test_crear_rango_valido(vacio):  # CP-### / REQ-009
    r = _post(vacio, E, "0.01", "999999.99")
    assert r.status_code == 201
    body = r.json()
    assert (body["level"], body["min"], body["max"]) == (E, "0.01", "999999.99")
    assert vacio.get(f"/api/approval-ranges/{body['id']}").json() == body


def test_traslape_por_un_centimo_409(vacio):  # CP-### / REQ-009
    assert _post(vacio, E, "0.01", "1000000.00").status_code == 201  # [1, 100000000)
    _error(_post(vacio, G, "999999.99", "10000000.00"), 409, "rango_traslapado")  # empieza 1 céntimo antes


def test_rangos_adyacentes_se_aceptan(vacio):  # CP-### / REQ-009
    assert _post(vacio, E, "0.01", "1000000.00").status_code == 201
    assert _post(vacio, G, "1000000.00", "10000000.00").status_code == 201
    assert _post(vacio, J, "10000000.00").status_code == 201


def test_huecos_se_permiten(vacio):  # CP-### / REQ-009
    assert _post(vacio, E, "0.01", "100.00").status_code == 201
    assert _post(vacio, G, "500.00", "900.00").status_code == 201


def test_maximo_nulo_con_otro_rango_por_encima_409(vacio):  # CP-### / REQ-009
    assert _post(vacio, G, "1000000.00").status_code == 201  # [1 000 000, infinito)
    _error(_post(vacio, J, "20000000.00", "30000000.00"), 409, "rango_traslapado")  # queda dentro del infinito


def test_maximo_nulo_debajo_de_otro_rango_409(vacio):  # CP-### / REQ-009
    assert _post(vacio, J, "10000000.00", "20000000.00").status_code == 201
    _error(_post(vacio, E, "0.01"), 409, "rango_traslapado")  # [0.01, infinito) incluye al existente


@pytest.mark.parametrize("minimo", ["0", "0.00", "-1.00", "abc", "", None])
def test_minimo_invalido_422(vacio, minimo):  # CP-### / REQ-009
    _error(_post(vacio, E, minimo, "5.00"), 422, "rango_invalido")


@pytest.mark.parametrize("maximo", ["10.00", "9.99", "0.01"])
def test_maximo_menor_o_igual_al_minimo_422(vacio, maximo):  # CP-### / REQ-009
    _error(_post(vacio, E, "10.00", maximo), 422, "rango_invalido")


def test_nivel_invalido_422(vacio):  # CP-### / REQ-009
    _error(_post(vacio, "Presidencia", "1.00", "2.00"), 422, "rango_invalido")


def test_nivel_duplicado_409(vacio):  # CP-### / REQ-009
    assert _post(vacio, E, "0.01", "100.00").status_code == 201
    _error(_post(vacio, E, "500.00", "600.00"), 409, "duplicado")  # no choca en montos, pero el nivel ya existe


def test_cuerpo_incompleto_422_con_formato_de_error(vacio):  # CP-### / REQ-011
    _error(vacio.post("/api/approval-ranges", json={"level": E}), 422, "validacion")


# ---- obtener / editar / borrar ----
def test_obtener_inexistente_404(adm):  # CP-### / REQ-011
    _error(adm.get("/api/approval-ranges/99999"), 404, "no_encontrado")


def test_editar_sin_chocar_consigo_mismo(adm):  # CP-### / REQ-009
    gerencia = next(r for r in adm.get("/api/approval-ranges").json() if r["level"] == G)
    # ampliar un poco su propio intervalo (sigue sin tocar a los vecinos): no debe verse como traslape consigo mismo
    r = adm.put(f"/api/approval-ranges/{gerencia['id']}", json={"level": G, "min": "1000000.00", "max": "9999999.99"})
    assert r.status_code == 200 and r.json()["max"] == "9999999.99"


def test_editar_con_traslape_con_otro_409_y_no_cambia(adm):  # CP-### / REQ-009
    gerencia = next(r for r in adm.get("/api/approval-ranges").json() if r["level"] == G)
    _error(
        adm.put(f"/api/approval-ranges/{gerencia['id']}", json={"level": G, "min": "999999.99", "max": "10000000.00"}),
        409, "rango_traslapado",
    )
    assert adm.get(f"/api/approval-ranges/{gerencia['id']}").json() == gerencia


def test_editar_a_nivel_de_otro_409_duplicado(adm):  # CP-### / REQ-009
    gerencia = next(r for r in adm.get("/api/approval-ranges").json() if r["level"] == G)
    _error(adm.put(f"/api/approval-ranges/{gerencia['id']}", json={"level": J, "min": "1000000.00", "max": "9999999.99"}), 409, "duplicado")


def test_editar_invalido_422(adm):  # CP-### / REQ-009
    rid = adm.get("/api/approval-ranges").json()[0]["id"]
    _error(adm.put(f"/api/approval-ranges/{rid}", json={"level": E, "min": "5.00", "max": "5.00"}), 422, "rango_invalido")


def test_editar_inexistente_404(adm):  # CP-### / REQ-011
    _error(adm.put("/api/approval-ranges/99999", json={"level": E, "min": "1.00"}), 404, "no_encontrado")


def test_borrar_204_y_se_puede_recrear(adm):  # CP-### / REQ-009
    gerencia = next(r for r in adm.get("/api/approval-ranges").json() if r["level"] == G)
    assert adm.delete(f"/api/approval-ranges/{gerencia['id']}").status_code == 204
    _error(adm.get(f"/api/approval-ranges/{gerencia['id']}"), 404, "no_encontrado")
    assert _post(adm, G, "1000000.00", "10000000.00").status_code == 201


def test_borrar_inexistente_404(adm):  # CP-### / REQ-011
    _error(adm.delete("/api/approval-ranges/99999"), 404, "no_encontrado")


def test_la_bd_rechaza_nivel_duplicado_y_responde_409(adm, monkeypatch):  # CP-### / REQ-009 / REQ-011
    from app.services import approval_ranges as service

    monkeypatch.setattr(service, "_check_unique_and_disjoint", lambda *a, **k: None)  # simula carrera: el UNIQUE sí lo ve
    _error(_post(adm, E, "5000000000.00", "6000000000.00"), 409, "duplicado")


# ---- permisos (REQ-011): solo admin ----
METHODS = [("get", "/api/approval-ranges"), ("post", "/api/approval-ranges"), ("get", "/api/approval-ranges/1"),
           ("put", "/api/approval-ranges/1"), ("delete", "/api/approval-ranges/1")]


def _call(client, method, path):
    body = {"json": {"level": E, "min": "1.00"}} if method in ("post", "put") else {}
    return getattr(client, method)(path, **body)


@pytest.mark.parametrize("method, path", METHODS)
def test_operador_recibe_403(client, seeded, login, method, path):  # CP-### / REQ-011
    assert login(*OPERADOR).status_code == 200
    _error(_call(client, method, path), 403, "prohibido")


@pytest.mark.parametrize("method, path", METHODS)
def test_sin_sesion_401(client, seeded, method, path):  # CP-### / REQ-011
    _error(_call(client, method, path), 401, "no_autenticado")


def test_operador_no_modifica_los_rangos(client, seeded, login, db):  # CP-### / REQ-011
    login(*OPERADOR)
    antes = [(r.level, r.min_cents, r.max_cents) for r in db.query(ApprovalRange).order_by(ApprovalRange.id)]
    _call(client, "post", "/api/approval-ranges")
    _call(client, "delete", f"/api/approval-ranges/{db.query(ApprovalRange).first().id}")
    db.expire_all()
    assert [(r.level, r.min_cents, r.max_cents) for r in db.query(ApprovalRange).order_by(ApprovalRange.id)] == antes
