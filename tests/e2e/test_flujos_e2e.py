"""Pruebas E2E (navegador real contra la app real): CP-011, CP-012, CP-013 y CP-020.

Resultado esperado = reglas de CLAUDE.md (REQ-001/002/004, 007/008/009, 010 y 011), no lo que hace el código.
Cada prueba arranca su servidor con el seed (ver conftest.py) y guarda capturas en 04_Evidencias/e2e/.
Correr:  pytest tests/e2e -m e2e
"""
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

NOMBRE_NUEVO = "Insumos del Sur E2E"
CODIGO_NUEVO = "LIC-E2E-001"


def _cierre_futuro() -> str:
    """Valor para <input type=datetime-local>: hora de Costa Rica (UTC−6) dentro de 3 días."""
    return (datetime.now(timezone.utc) - timedelta(hours=6) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")


def _hoy_cr() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%d/%m/%Y")


def _crear_proveedor(page, url, nombre, email="ventas@sur.cr"):
    page.goto(f"{url}/providers/new")
    page.get_by_test_id("provider-name-input").fill(nombre)
    page.get_by_test_id("provider-email-input").fill(email)
    page.get_by_test_id("provider-submit").click()


def test_flujo_alta_proveedor_licitacion_publicar_y_ofertar(page, servidor, iniciar_sesion, captura):  # CP-011 / REQ-001 / REQ-002 / REQ-004
    url = servidor.url
    iniciar_sesion()
    expect(page.get_by_test_id("nav-user")).to_be_visible()
    captura("EV-011", "CP-011", "01_login_panel")

    # 1) Proveedor nuevo (REQ-001)
    _crear_proveedor(page, url, NOMBRE_NUEVO)
    expect(page.get_by_test_id("flash-success").first).to_contain_text(f"Proveedor {NOMBRE_NUEVO} creado.")
    expect(page.get_by_test_id("providers-table")).to_contain_text(NOMBRE_NUEVO)
    captura("EV-011", "CP-011", "02_proveedor_creado")

    # 2) Licitación nueva: queda en Borrador (REQ-002)
    page.goto(f"{url}/tenders/new")
    page.get_by_test_id("tender-code-input").fill(CODIGO_NUEVO)
    page.get_by_test_id("tender-title-input").fill("Compra de insumos E2E")
    page.get_by_test_id("tender-budget-input").fill("1000000.00")
    page.get_by_test_id("tender-closes-at-input").fill(_cierre_futuro())
    page.get_by_test_id("tender-submit").click()
    expect(page.get_by_test_id("flash-success").first).to_contain_text(f"Licitación {CODIGO_NUEVO} creada en estado Borrador.")
    expect(page.get_by_test_id("tender-detail-code")).to_have_text(CODIGO_NUEVO)
    expect(page.get_by_test_id("status-badge").first).to_have_text("Borrador")
    expect(page.get_by_test_id("tender-detail-budget")).to_contain_text("₡1 000 000,00")
    captura("EV-011", "CP-011", "03_licitacion_borrador")

    # 3) Publicar (REQ-003): pasa a Publicada y ya acepta ofertas (REQ-004)
    page.get_by_test_id("tender-publish").click()
    expect(page.get_by_test_id("status-badge").first).to_have_text("Publicada")
    expect(page.get_by_test_id("offer-form")).to_be_visible()
    captura("EV-011", "CP-011", "04_licitacion_publicada")

    # 4) Ofertar con el proveedor nuevo, antes del cierre (REQ-004, REQ-005)
    page.get_by_test_id("offer-provider-input").select_option(label=NOMBRE_NUEVO)
    page.get_by_test_id("offer-amount-input").fill("900000.00")
    page.get_by_test_id("offer-submit").click()
    expect(page.get_by_test_id("flash-success").first).to_contain_text(f"Oferta de {NOMBRE_NUEVO} registrada.")
    expect(page.get_by_test_id("offers-count")).to_have_text("1")
    expect(page.get_by_test_id("offers-table")).to_contain_text(NOMBRE_NUEVO)
    expect(page.get_by_test_id("offers-table")).to_contain_text("₡900 000,00")
    # la evaluación refleja la oferta: mejor oferta del proveedor nuevo, ahorro 10 % (REQ-007/008)
    expect(page.get_by_test_id("evaluation-best-provider")).to_have_text(NOMBRE_NUEVO)
    expect(page.get_by_test_id("evaluation-savings")).to_have_text("10,00 %")
    captura("EV-011", "CP-011", "05_oferta_registrada")


def test_detalle_de_l1_muestra_mejor_oferta_ahorro_clasificacion_y_aprobador(page, servidor, iniciar_sesion, captura):  # CP-012 / REQ-007 / REQ-008 / REQ-009
    iniciar_sesion()
    page.goto(f"{servidor.url}/tenders")
    page.get_by_test_id("tender-view-1").click()  # L1 del seed: LIC-2026-001
    expect(page.get_by_test_id("tender-detail-code")).to_have_text("LIC-2026-001")
    expect(page.get_by_test_id("tender-detail-budget")).to_contain_text("₡10 000 000,00")
    expect(page.get_by_test_id("offers-count")).to_have_text("2")
    expect(page.get_by_test_id("evaluation-best-provider")).to_have_text("Tecnología Norte S.A.")  # P1
    expect(page.get_by_test_id("evaluation-best-amount")).to_have_text("₡9 000 000,00")
    expect(page.get_by_test_id("evaluation-savings")).to_have_text("10,00 %")
    expect(page.get_by_test_id("evaluation-classification")).to_have_text("Conveniente")
    expect(page.get_by_test_id("evaluation-approver")).to_have_text("Gerencia")
    captura("EV-012", "CP-012", "01_detalle_l1_evaluacion")


def test_vista_usd_de_l1_muestra_tasa_y_fecha_y_no_cambia_los_importes(page, servidor, iniciar_sesion, captura):  # CP-013 / REQ-010
    url = servidor.url
    iniciar_sesion()

    def importes_en_bd():  # lo guardado, vía API (misma sesión del navegador)
        r = page.context.request.get(f"{url}/api/tenders/1/offers")
        assert r.ok
        return [(o["id"], o["amount"]) for o in r.json()]

    antes = importes_en_bd()
    assert antes == [(1, "9000000.00"), (2, "9500000.00")]

    page.goto(f"{url}/tenders/1")
    expect(page.get_by_test_id("offer-amount-1")).to_have_text("₡9 000 000,00")
    expect(page.get_by_test_id("rate-info")).to_have_count(0)
    captura("EV-013", "CP-013", "01_l1_en_crc")

    page.get_by_test_id("currency-usd").click()
    expect(page.get_by_test_id("offer-amount-1")).to_have_text("$18 000,00")  # 9 000 000 / 500
    expect(page.get_by_test_id("offer-amount-2")).to_have_text("$19 000,00")  # 9 500 000 / 500
    expect(page.get_by_test_id("evaluation-best-amount")).to_have_text("$18 000,00")
    expect(page.get_by_test_id("evaluation-rate")).to_contain_text("₡500.00 por USD")  # tasa usada
    expect(page.get_by_test_id("evaluation-rate")).to_contain_text(_hoy_cr())  # fecha de la tasa
    expect(page.get_by_test_id("rate-info")).to_contain_text("₡500.00 por USD")
    expect(page.get_by_test_id("evaluation-approver")).to_have_text("Gerencia")  # el nivel se decide en CRC
    assert importes_en_bd() == antes  # alternar la vista NO toca la BD
    captura("EV-013", "CP-013", "02_l1_en_usd")

    page.get_by_test_id("currency-crc").click()
    expect(page.get_by_test_id("offer-amount-1")).to_have_text("₡9 000 000,00")
    expect(page.get_by_test_id("offer-amount-2")).to_have_text("₡9 500 000,00")
    expect(page.get_by_test_id("rate-info")).to_have_count(0)
    assert importes_en_bd() == antes
    captura("EV-013", "CP-013", "03_l1_vuelve_a_crc")


def test_proveedor_creado_sigue_en_el_listado_tras_reiniciar_el_servidor(page, servidor, iniciar_sesion, captura):  # CP-020 / REQ-011
    url = servidor.url
    iniciar_sesion()
    _crear_proveedor(page, url, "Proveedor Persistente E2E", "persistente@e2e.cr")
    expect(page.get_by_test_id("providers-table")).to_contain_text("Proveedor Persistente E2E")
    captura("EV-014", "CP-020", "01_proveedor_antes_de_reiniciar")

    servidor.reiniciar()  # se detiene uvicorn y se levanta de nuevo con la MISMA BD (sin volver a sembrar)

    page.goto(f"{url}/providers")
    if "/login" in page.url:  # por si la sesión no sobreviviera al reinicio
        iniciar_sesion()
        page.goto(f"{url}/providers")
    expect(page.get_by_test_id("providers-table")).to_contain_text("Proveedor Persistente E2E")
    expect(page.get_by_test_id("providers-table")).to_contain_text("persistente@e2e.cr")
    expect(page.get_by_test_id("providers-table")).to_contain_text("Tecnología Norte S.A.")  # el seed también sigue
    captura("EV-014", "CP-020", "02_proveedor_despues_de_reiniciar")
