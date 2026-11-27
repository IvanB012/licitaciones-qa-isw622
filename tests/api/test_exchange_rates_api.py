"""API de tipo de cambio (contrato §5). Esperado: REQ-010, REQ-011 y REQ-012 de CLAUDE.md."""
import pytest
from sqlalchemy import select

from app.exchange import FailingExchangeRateProvider, FakeExchangeRateProvider
from app.models import ExchangeRate, Offer, Tender
from tests.conftest import OPERADOR

HOY = "2026-11-26"  # el FakeClock arranca el 2026-11-26 12:00Z (06:00 en Costa Rica)


@pytest.fixture
def op(client, seeded, login):
    """Sesión de operador y datos de referencia (el seed trae una tasa 500.00 'seed')."""
    assert login(*OPERADOR).status_code == 200
    return client


@pytest.fixture
def sin_tasas(op, db):
    db.query(ExchangeRate).delete()
    db.commit()


def _error(r, status, code):
    assert r.status_code == status, r.text
    assert r.json()["error"] == code
    assert set(r.json()) == {"error", "detalle"}


# ---- crear (REQ-010) ----
def test_crear_tasa_manual_por_defecto(op):  # REQ-010
    r = op.post("/api/exchange-rates", json={"rate": "512.50"})
    assert r.status_code == 201
    body = r.json()
    assert (body["rate"], body["rate_date"], body["source"]) == ("512.50", HOY, "manual")
    assert op.get(f"/api/exchange-rates/{body['id']}").json() == body


def test_crear_con_fuente_sugerida_y_fecha_oficial(op):  # REQ-010
    r = op.post("/api/exchange-rates", json={"rate": "501.1234", "rate_date": HOY, "source": "sugerida"})
    assert r.status_code == 201 and r.json()["rate"] == "501.1234" and r.json()["source"] == "sugerida"


@pytest.mark.parametrize("rate", ["0", "0.00", "-5", "abc", "", "500.12345", "5e2", None, 500])
def test_tasa_invalida_422(op, rate):  # REQ-010
    _error(op.post("/api/exchange-rates", json={"rate": rate}), 422, "tasa_invalida")


@pytest.mark.parametrize("fecha", ["2026-11-25", "2026-11-27", "ayer"])
def test_fecha_distinta_de_la_oficial_422(op, fecha):  # REQ-010
    _error(op.post("/api/exchange-rates", json={"rate": "500.00", "rate_date": fecha}), 422, "tasa_invalida")


@pytest.mark.parametrize("source", ["seed", "externo", "otra"])
def test_fuente_invalida_422(op, source):  # REQ-010
    _error(op.post("/api/exchange-rates", json={"rate": "500.00", "source": source}), 422, "tasa_invalida")


def test_tasa_enorme_no_da_500(op):  # REQ-011
    _error(op.post("/api/exchange-rates", json={"rate": "999999999999999"}), 422, "tasa_invalida")


# ---- listar / vigente (REQ-010) ----
def test_listar_mas_reciente_primero(op, clock):  # REQ-010
    primero = op.post("/api/exchange-rates", json={"rate": "510.00"}).json()["id"]
    segundo = op.post("/api/exchange-rates", json={"rate": "520.00"}).json()["id"]
    ids = [r["id"] for r in op.get("/api/exchange-rates").json()]
    assert ids.index(segundo) < ids.index(primero)
    assert ids[0] == segundo


def test_current_sin_tasas_guardadas_es_500_seed(sin_tasas, op):  # REQ-010
    r = op.get("/api/exchange-rates/current")
    assert r.status_code == 200
    assert r.json() == {"rate": "500.00", "rate_date": HOY, "source": "seed"}


def test_current_con_una_tasa_guardada(sin_tasas, op):  # REQ-010
    op.post("/api/exchange-rates", json={"rate": "507.25"})
    assert op.get("/api/exchange-rates/current").json() == {"rate": "507.25", "rate_date": HOY, "source": "manual"}


def test_current_del_seed_tiene_tasa_500(op):  # REQ-010
    body = op.get("/api/exchange-rates/current").json()
    assert body["rate"] == "500.00" and body["rate_date"] == HOY


# ---- sugerir (REQ-010): solo sugiere, no guarda ----
def test_suggest_con_proveedor_fake(op, app, db):  # REQ-010
    app.state.rate_provider = FakeExchangeRateProvider("500.00")
    antes = db.query(ExchangeRate).count()
    r = op.get("/api/exchange-rates/suggest")
    assert r.status_code == 200 and r.json() == {"rate": "500.00", "source": "externo"}
    db.expire_all()
    assert db.query(ExchangeRate).count() == antes  # no guarda


def test_suggest_redondea_a_4_decimales(op, app):  # REQ-010
    app.state.rate_provider = FakeExchangeRateProvider("512.345678")
    assert op.get("/api/exchange-rates/suggest").json()["rate"] == "512.3457"


def test_suggest_con_proveedor_que_falla_usa_respaldo_con_aviso(op, app, db):  # REQ-010
    assert isinstance(app.state.rate_provider, FailingExchangeRateProvider)
    antes = db.query(ExchangeRate).count()
    r = op.get("/api/exchange-rates/suggest")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "respaldo" and body["rate"] == "500.00" and body["aviso"]
    db.expire_all()
    assert db.query(ExchangeRate).count() == antes


def test_suggest_respaldo_usa_la_ultima_tasa_guardada(op):  # REQ-010
    op.post("/api/exchange-rates", json={"rate": "531.00"})
    assert op.get("/api/exchange-rates/suggest").json()["rate"] == "531.00"


@pytest.mark.parametrize("valor", ["0", "-5"])
def test_suggest_con_valor_inutilizable_cae_al_respaldo(op, app, valor):  # REQ-010
    app.state.rate_provider = FakeExchangeRateProvider(valor)
    assert op.get("/api/exchange-rates/suggest").json()["source"] == "respaldo"


# ---- obtener / editar / borrar ----
def test_obtener_inexistente_404(op):  # REQ-011
    _error(op.get("/api/exchange-rates/99999"), 404, "no_encontrado")


def test_editar_tasa_conserva_fuente(op):  # REQ-010
    rid = op.post("/api/exchange-rates", json={"rate": "510.00", "source": "sugerida"}).json()["id"]
    r = op.put(f"/api/exchange-rates/{rid}", json={"rate": "515.5", "rate_date": HOY})
    assert r.status_code == 200
    assert (r.json()["rate"], r.json()["source"]) == ("515.50", "sugerida")


def test_editar_tasa_del_seed_sin_enviar_fecha(op, seeded):  # REQ-010
    r = op.put(f"/api/exchange-rates/{seeded.exchange_rate_id}", json={"rate": "505.00"})
    assert r.status_code == 200 and r.json()["rate"] == "505.00"


@pytest.mark.parametrize("body", [{"rate": "0"}, {"rate": "abc"}, {"rate": "1.23456"}, {"rate": "500", "rate_date": "2026-01-01"}])
def test_editar_invalido_422_y_no_cambia(op, seeded, body):  # REQ-010
    _error(op.put(f"/api/exchange-rates/{seeded.exchange_rate_id}", json=body), 422, "tasa_invalida")
    assert op.get(f"/api/exchange-rates/{seeded.exchange_rate_id}").json()["rate"] == "500.00"


def test_editar_inexistente_404(op):  # REQ-011
    _error(op.put("/api/exchange-rates/99999", json={"rate": "500"}), 404, "no_encontrado")


def test_borrar_204_y_luego_404(op):  # REQ-010
    rid = op.post("/api/exchange-rates", json={"rate": "510.00"}).json()["id"]
    assert op.delete(f"/api/exchange-rates/{rid}").status_code == 204
    _error(op.get(f"/api/exchange-rates/{rid}"), 404, "no_encontrado")


def test_borrar_todas_las_tasas_vuelve_al_respaldo(op, seeded):  # REQ-010
    assert op.delete(f"/api/exchange-rates/{seeded.exchange_rate_id}").status_code == 204
    assert op.get("/api/exchange-rates/current").json()["source"] == "seed"


def test_borrar_inexistente_404(op):  # REQ-011
    _error(op.delete("/api/exchange-rates/99999"), 404, "no_encontrado")


# ---- sesión (REQ-011) ----
@pytest.mark.parametrize(
    "method, path",
    [("get", "/api/exchange-rates"), ("post", "/api/exchange-rates"), ("get", "/api/exchange-rates/current"),
     ("get", "/api/exchange-rates/suggest"), ("get", "/api/exchange-rates/1"), ("put", "/api/exchange-rates/1"),
     ("delete", "/api/exchange-rates/1")],
)
def test_sin_sesion_401(client, seeded, method, path):  # REQ-011
    r = getattr(client, method)(path, **({"json": {"rate": "500"}} if method in ("post", "put") else {}))
    _error(r, 401, "no_autenticado")


# ---- alternar CRC/USD no modifica la BD (REQ-010) ----
def test_alternar_moneda_no_cambia_la_bd(op, db, seeded):  # REQ-010
    def foto():
        db.expire_all()
        return (
            db.query(ExchangeRate).count(), db.query(Tender).count(), db.query(Offer).count(),
            [(t.id, t.budget_cents) for t in db.scalars(select(Tender).order_by(Tender.id))],
            [(o.id, o.amount_cents) for o in db.scalars(select(Offer).order_by(Offer.id))],
            [(e.id, e.rate_x10000) for e in db.scalars(select(ExchangeRate).order_by(ExchangeRate.id))],
        )

    antes = foto()
    for currency in ("USD", "CRC", "USD", "USD", "CRC", "USD"):
        for path in ("/tenders", f"/tenders/{seeded.tender_id}", "/exchange-rates"):
            assert op.get(f"{path}?currency={currency}").status_code == 200
    assert foto() == antes
    assert antes[3][0][1] == 1_000_000_000 and antes[4][0][1] == 900_000_000  # siguen en céntimos CRC


def test_usd_es_crc_entre_tasa_con_tasa_y_fecha_visibles(op, seeded):  # REQ-010
    page = op.get(f"/tenders/{seeded.tender_id}?currency=USD").text
    assert "$18 000,00" in page  # 9 000 000,00 / 500,00 (oferta de P1)
    assert 'data-testid="rate-info"' in page and "₡500.00" in page and "26/11/2026" in page
    assert "$20 000,00" in page  # presupuesto 10 000 000,00 / 500,00


def test_usd_usa_la_tasa_guardada_mas_reciente(op, seeded):  # REQ-010
    op.post("/api/exchange-rates", json={"rate": "600.00"})
    page = op.get(f"/tenders/{seeded.tender_id}?currency=USD").text
    assert "$15 000,00" in page and "₡600.00" in page  # 9 000 000 / 600
