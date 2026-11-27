"""UI de tipo de cambio: mismas reglas y mensajes que la API (REQ-010, REQ-011)."""
import socket

import httpx
import pytest

from app.config import Settings
from app.exchange import FailingExchangeRateProvider, FakeExchangeRateProvider, HttpExchangeRateProvider
from app.main import create_app
from app.models import ExchangeRate
from tests.conftest import OPERADOR


@pytest.fixture
def ui(client, seeded):
    r = client.post("/login", data={"username": OPERADOR[0], "password": OPERADOR[1]}, follow_redirects=False)
    assert r.status_code == 303
    return client


def _new(ui, rate="512.50", rate_date="2026-11-26", source="manual"):
    return ui.post("/exchange-rates/new", data={"rate": rate, "rate_date": rate_date, "source": source}, follow_redirects=False)


def test_rutas_exigen_sesion(client, seeded):  # REQ-011
    for path in ("/exchange-rates", "/exchange-rates/new", f"/exchange-rates/{seeded.exchange_rate_id}/edit"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.post("/exchange-rates/suggest", follow_redirects=False).headers["location"] == "/login"


def test_listado_muestra_tasa_vigente_con_fecha_y_testids(ui, seeded):  # REQ-010
    page = ui.get("/exchange-rates").text
    assert 'data-testid="current-rate">500.00<' in page
    assert 'data-testid="current-rate-date">26/11/2026<' in page
    assert f'data-testid="exchange-rate-row-{seeded.exchange_rate_id}"' in page
    assert 'data-testid="exchange-rate-new"' in page


def test_formulario_tiene_testids_y_boton_sugerir(ui):  # REQ-013
    page = ui.get("/exchange-rates/new").text
    for testid in ("exchange-rate-rate-input", "exchange-rate-date-input", "exchange-rate-submit", "exchange-rate-suggest"):
        assert f'data-testid="{testid}"' in page
    assert 'value="2026-11-26"' in page  # fecha oficial por defecto


def test_alta_correcta_actualiza_la_vigente(ui, db):  # REQ-010
    r = _new(ui)
    assert r.status_code == 303 and r.headers["location"] == "/exchange-rates"
    page = ui.get("/exchange-rates")
    assert 'data-testid="flash-success"' in page.text and 'data-testid="current-rate">512.50<' in page.text
    assert db.query(ExchangeRate).filter_by(rate_x10000=5_125_000, source="manual").count() == 1


@pytest.mark.parametrize(
    "rate, fecha, fragmento",
    [("0", "2026-11-26", "mayor que cero"), ("-5", "2026-11-26", "inválida"), ("abc", "2026-11-26", "inválida"),
     ("500.12345", "2026-11-26", "4 decimales"), ("500", "2026-11-25", "fecha oficial")],
)
def test_alta_con_error_se_muestra_en_error_message(ui, rate, fecha, fragmento):  # REQ-010
    r = _new(ui, rate, fecha)
    assert r.status_code == 422
    assert 'data-testid="error-message"' in r.text and fragmento in r.text
    assert f'value="{rate}"' in r.text  # conserva lo escrito


def test_error_ui_usa_el_mismo_detalle_que_la_api(ui):  # REQ-011
    api = ui.post("/api/exchange-rates", json={"rate": "0"})
    assert api.json()["detalle"] in _new(ui, "0").text


def test_sugerir_con_proveedor_fake_rellena_sin_guardar(ui, app, db):  # REQ-010
    app.state.rate_provider = FakeExchangeRateProvider("507.1234")
    antes = db.query(ExchangeRate).count()
    r = ui.post("/exchange-rates/suggest")
    assert r.status_code == 200
    assert 'value="507.1234"' in r.text and 'name="source" value="sugerida"' in r.text
    assert 'data-testid="suggest-notice"' not in r.text
    db.expire_all()
    assert db.query(ExchangeRate).count() == antes  # el usuario aún no confirmó
    # confirmar con "Guardar" crea la tasa con fuente "sugerida"
    assert _new(ui, "507.1234", "2026-11-26", "sugerida").status_code == 303
    assert db.query(ExchangeRate).filter_by(rate_x10000=5_071_234, source="sugerida").count() == 1


def test_sugerir_con_servicio_caido_muestra_respaldo_y_aviso(ui, app, db):  # REQ-010
    assert isinstance(app.state.rate_provider, FailingExchangeRateProvider)
    antes = db.query(ExchangeRate).count()
    r = ui.post("/exchange-rates/suggest")
    assert r.status_code == 200
    assert 'data-testid="suggest-notice"' in r.text and "no está disponible" in r.text
    assert 'value="500.00"' in r.text and 'name="source" value="manual"' in r.text
    db.expire_all()
    assert db.query(ExchangeRate).count() == antes


def test_editar_y_borrar_por_ui(ui, seeded, db):  # REQ-010
    r = ui.post(f"/exchange-rates/{seeded.exchange_rate_id}/edit", data={"rate": "505", "rate_date": "2026-11-26"}, follow_redirects=False)
    assert r.status_code == 303
    assert 'data-testid="current-rate">505.00<' in ui.get("/exchange-rates").text
    bad = ui.post(f"/exchange-rates/{seeded.exchange_rate_id}/edit", data={"rate": "0", "rate_date": "2026-11-26"})
    assert bad.status_code == 422 and 'data-testid="error-message"' in bad.text
    assert ui.post(f"/exchange-rates/{seeded.exchange_rate_id}/delete", follow_redirects=False).status_code == 303
    db.expire_all()
    assert db.get(ExchangeRate, seeded.exchange_rate_id) is None
    assert 'data-testid="current-rate-source">seed<' in ui.get("/exchange-rates").text


def test_editar_inexistente_404(ui):  # REQ-011
    assert ui.get("/exchange-rates/99999/edit").status_code == 404


# ---- ninguna prueba toca la red (CLAUDE.md: proveedor falso que devuelve 500) ----
def test_la_app_de_pruebas_usa_proveedor_falso(app):  # REQ-010
    assert isinstance(app.state.rate_provider, (FailingExchangeRateProvider, FakeExchangeRateProvider))
    assert not isinstance(app.state.rate_provider, HttpExchangeRateProvider)


def test_create_app_con_env_test_nunca_usa_http(settings):  # REQ-010
    assert isinstance(create_app(settings=settings).state.rate_provider, FailingExchangeRateProvider)


def test_create_app_real_usa_proveedor_http_con_la_url_configurada(tmp_path):  # REQ-010
    real = Settings(database_url=f"sqlite:///{tmp_path / 'r.db'}", env="dev", exchange_rate_url="http://ejemplo.invalido/x")
    provider = create_app(settings=real).state.rate_provider
    assert isinstance(provider, HttpExchangeRateProvider) and provider._url == "http://ejemplo.invalido/x"


def test_la_red_esta_bloqueada_en_pruebas():  # REQ-010
    with pytest.raises(OSError):
        socket.getaddrinfo("open.er-api.com", 443)
    with pytest.raises(httpx.HTTPError):  # httpx lo reporta como error de conexión, no llega a ningún servidor
        httpx.get("https://open.er-api.com/v6/latest/USD", timeout=1)
