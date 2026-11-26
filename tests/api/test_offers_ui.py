"""UI de ofertas: mismas reglas y mismos mensajes que la API (REQ-004, 005, 006, 010, 011, 012)."""
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.models import Offer, Provider
from app.rules.normalization import normalize_name
from tests.conftest import OPERADOR


@pytest.fixture
def ui(client, seeded):
    r = client.post("/login", data={"username": OPERADOR[0], "password": OPERADOR[1]}, follow_redirects=False)
    assert r.status_code == 303
    client.get("/")  # consume el mensaje de bienvenida
    return client


@pytest.fixture
def p3(db, clock):
    p = Provider(name="Soluciones Pacífico", name_key=normalize_name("Soluciones Pacífico"), created_at=clock.now())
    db.add(p)
    db.commit()
    return p


def _post(ui, tender_id, provider_id, amount):
    return ui.post(
        f"/tenders/{tender_id}/offers", data={"provider_id": str(provider_id), "amount": amount}, follow_redirects=False
    )


def _count(db):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Offer))


def test_detalle_muestra_ofertas_y_formulario(ui, seeded):
    page = ui.get(f"/tenders/{seeded.tender_id}").text
    assert 'data-testid="offers-table"' in page and 'data-testid="offer-form"' in page
    for o_id, nombre, monto in ((seeded.offer_p1_id, "Tecnología Norte S.A.", "₡9 000 000,00"),
                                (seeded.offer_p2_id, "Servicios del Valle", "₡9 500 000,00")):
        assert f'data-testid="offer-row-{o_id}"' in page and nombre in page and monto in page
    for testid in ("offer-provider-input", "offer-amount-input", "offer-submit"):
        assert f'data-testid="{testid}"' in page


def test_registrar_oferta_por_ui(ui, seeded, p3, db):  # REQ-005
    r = _post(ui, seeded.tender_id, p3.id, "9800000.00")
    assert r.status_code == 303 and r.headers["location"] == f"/tenders/{seeded.tender_id}"
    page = ui.get(r.headers["location"]).text
    assert 'data-testid="flash-success"' in page and "Soluciones Pacífico" in page and "₡9 800 000,00" in page
    assert _count(db) == 3


def test_errores_de_ui_muestran_el_mismo_detalle_que_la_api(ui, seeded, p3):  # REQ-011
    api = ui.post(f"/api/tenders/{seeded.tender_id}/offers", json={"provider_id": p3.id, "amount": "10000000.01"})
    r = _post(ui, seeded.tender_id, p3.id, "10000000.01")
    assert r.status_code == 422
    assert 'data-testid="error-message"' in r.text and "superar el presupuesto" in r.text
    assert api.json()["detalle"].replace("₡", "&#8353;") in r.text or api.json()["detalle"] in r.text


@pytest.mark.parametrize(
    "monto, status, fragmento",
    [
        ("10000000.01", 422, "superar el presupuesto"),  # REQ-005
        ("0", 422, "mayor que cero"),
        ("-5", 422, "mayor que cero"),
        ("abc", 422, "Monto inválido"),
        ("", 422, "Monto inválido"),
    ],
)
def test_montos_rechazados_por_ui_no_se_guardan(ui, seeded, p3, db, monto, status, fragmento):  # REQ-005
    r = _post(ui, seeded.tender_id, p3.id, monto)
    assert r.status_code == status and fragmento in r.text
    assert _count(db) == 2


def test_oferta_igual_al_presupuesto_es_valida_por_ui(ui, seeded, p3, db):  # REQ-005
    assert _post(ui, seeded.tender_id, p3.id, "10000000.00").status_code == 303
    assert _count(db) == 3


def test_duplicado_rechazado_por_ui(ui, seeded, db):  # REQ-006
    r = _post(ui, seeded.tender_id, seeded.p1_id, "8000000.00")
    assert r.status_code == 409 and "ya presentó una oferta" in r.text
    assert _count(db) == 2


def test_sin_proveedor_seleccionado(ui, seeded, db):
    r = ui.post(f"/tenders/{seeded.tender_id}/offers", data={"provider_id": "", "amount": "1.00"}, follow_redirects=False)
    assert r.status_code == 422 and "Seleccione un proveedor" in r.text
    assert _count(db) == 2


def test_oferta_exactamente_en_el_cierre_rechazada_por_ui(ui, seeded, p3, clock, db):  # REQ-004
    clock.set(clock.now() + timedelta(hours=48))
    r = _post(ui, seeded.tender_id, p3.id, "9000000.00")
    assert r.status_code == 409 and "venció el plazo" in r.text
    assert _count(db) == 2


def test_licitacion_vencida_oculta_el_formulario(ui, seeded, clock):  # REQ-004 (vista)
    assert 'data-testid="offer-form"' in ui.get(f"/tenders/{seeded.tender_id}").text
    clock.set(clock.now() + timedelta(hours=48))
    page = ui.get(f"/tenders/{seeded.tender_id}").text
    assert 'data-testid="offer-form"' not in page and 'data-testid="offers-closed-note"' in page
    assert f'data-testid="offer-edit-{seeded.offer_p1_id}"' not in page


def test_licitacion_cerrada_no_acepta_ofertas_por_ui(ui, seeded, p3, db):  # REQ-004
    ui.post(f"/tenders/{seeded.tender_id}/close", follow_redirects=False)
    page = ui.get(f"/tenders/{seeded.tender_id}").text
    assert 'data-testid="offer-form"' not in page and "cerrada" in page
    assert _post(ui, seeded.tender_id, p3.id, "9000000.00").status_code == 409
    assert _count(db) == 2


def test_editar_oferta_por_ui(ui, seeded, db):  # REQ-005
    page = ui.get(f"/offers/{seeded.offer_p2_id}/edit")
    assert page.status_code == 200 and 'value="9500000.00"' in page.text and "Servicios del Valle" in page.text
    r = ui.post(f"/offers/{seeded.offer_p2_id}/edit", data={"amount": "8800000.00"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/tenders/{seeded.tender_id}"
    db.expire_all()
    assert db.get(Offer, seeded.offer_p2_id).amount_cents == 880_000_000


def test_editar_con_monto_invalido_muestra_error_y_no_guarda(ui, seeded, db):  # REQ-005
    r = ui.post(f"/offers/{seeded.offer_p2_id}/edit", data={"amount": "10000000.01"}, follow_redirects=False)
    assert r.status_code == 422 and 'data-testid="error-message"' in r.text and 'value="10000000.01"' in r.text
    db.expire_all()
    assert db.get(Offer, seeded.offer_p2_id).amount_cents == 950_000_000


def test_eliminar_oferta_por_ui(ui, seeded, db):
    r = ui.post(f"/offers/{seeded.offer_p2_id}/delete", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/tenders/{seeded.tender_id}"
    assert _count(db) == 1


def test_eliminar_con_licitacion_vencida_muestra_error(ui, seeded, clock, db):  # REQ-004
    clock.set(clock.now() + timedelta(hours=48))
    ui.post(f"/offers/{seeded.offer_p2_id}/delete", follow_redirects=False)
    page = ui.get(f"/tenders/{seeded.tender_id}").text
    assert 'data-testid="flash-error"' in page and "venció el plazo" in page
    assert _count(db) == 2


def test_oferta_inexistente_404_en_ui(ui):
    assert ui.get("/offers/9999/edit").status_code == 404


def test_nombre_de_proveedor_con_html_se_escapa(ui, seeded, db, clock):  # REQ-012
    malo = Provider(name="<script>alert(1)</script>", name_key="x", created_at=clock.now())
    db.add(malo)
    db.commit()
    assert _post(ui, seeded.tender_id, malo.id, "9000000.00").status_code == 303
    page = ui.get(f"/tenders/{seeded.tender_id}").text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_vista_usd_de_ofertas_no_modifica_la_bd(ui, seeded, db):  # REQ-010
    page = ui.get(f"/tenders/{seeded.tender_id}?currency=USD").text
    assert "$18 000,00" in page and "$19 000,00" in page  # 9 000 000 / 500 y 9 500 000 / 500
    db.expire_all()
    assert [db.get(Offer, i).amount_cents for i in (seeded.offer_p1_id, seeded.offer_p2_id)] == [900_000_000, 950_000_000]


def test_rutas_de_ofertas_exigen_sesion(client, seeded):
    for method, path in (("post", f"/tenders/{seeded.tender_id}/offers"), ("get", f"/offers/{seeded.offer_p1_id}/edit"),
                         ("post", f"/offers/{seeded.offer_p1_id}/edit"), ("post", f"/offers/{seeded.offer_p1_id}/delete")):
        r = getattr(client, method)(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"
