# Pruebas automatizadas representativas

- **Framework:** pytest **9.2.0** (obtenido con `.venv/Scripts/python -m pytest --version`), Python 3.15.2, entorno virtual `.venv`.
- **Red:** ninguna prueba toca la red (fixture `no_network` y proveedor de tipo de cambio falso).
- **Suite completa:** `.venv/Scripts/python -m pytest -q` (928 pruebas en verde al preparar este documento, unos 2 min 40 s).
- **Una prueba:** `.venv/Scripts/python -m pytest "<node id>" -v`. En nodos parametrizados, el node id sin corchetes ejecuta todas las variantes.
- Todas se ejecutan sobre una BD temporal propia (`tmp_path`), sin afectar `licitaciones.db`.

## Unitarias (7)

| # | CP | REQ | Ruta y node id | Comando |
|---|---|---|---|---|
| 1 | CP-001 | REQ-001 | `tests/unit/test_provider_rules.py::test_nombres_equivalentes_tienen_la_misma_clave` | `.venv/Scripts/python -m pytest tests/unit/test_provider_rules.py::test_nombres_equivalentes_tienen_la_misma_clave -v` |
| 2 | CP-002 | REQ-005 | `tests/unit/test_offer_rules.py::test_monto_sobre_el_presupuesto_se_rechaza` | `.venv/Scripts/python -m pytest tests/unit/test_offer_rules.py::test_monto_sobre_el_presupuesto_se_rechaza -v` |
| 3 | CP-003 | REQ-004 | `tests/unit/test_offer_rules.py::test_exactamente_en_el_cierre_se_rechaza` | `.venv/Scripts/python -m pytest tests/unit/test_offer_rules.py::test_exactamente_en_el_cierre_se_rechaza -v` |
| 4 | CP-004 | REQ-003 | `tests/unit/test_tender_rules.py::test_transiciones_invalidas` | `.venv/Scripts/python -m pytest tests/unit/test_tender_rules.py::test_transiciones_invalidas -v` |
| 5 | CP-005 | REQ-008 | `tests/unit/test_evaluation_rules.py::test_escenario_aislado_10_5_y_0_por_ciento` | `.venv/Scripts/python -m pytest tests/unit/test_evaluation_rules.py::test_escenario_aislado_10_5_y_0_por_ciento -v` |
| 6 | CP-006 | REQ-009 | `tests/unit/test_evaluation_rules.py::test_aprobador_por_rango` | `.venv/Scripts/python -m pytest tests/unit/test_evaluation_rules.py::test_aprobador_por_rango -v` |
| 7 | CP-007 | REQ-010 | `tests/unit/test_money.py::test_crc_a_usd_exige_tasa_positiva` | `.venv/Scripts/python -m pytest tests/unit/test_money.py::test_crc_a_usd_exige_tasa_positiva -v` |

## API / integración (5)

| # | CP | REQ | Ruta y node id | Comando |
|---|---|---|---|---|
| 8 | CP-008 | REQ-006 | `tests/api/test_offers_api.py::test_proveedor_no_puede_ofertar_dos_veces` | `.venv/Scripts/python -m pytest tests/api/test_offers_api.py::test_proveedor_no_puede_ofertar_dos_veces -v` |
| 9 | CP-009 | REQ-002, REQ-011 | `tests/api/test_tenders_api.py::test_codigo_duplicado_sin_distinguir_mayusculas_ni_espacios` | `.venv/Scripts/python -m pytest tests/api/test_tenders_api.py::test_codigo_duplicado_sin_distinguir_mayusculas_ni_espacios -v` |
| 10 | CP-010 | REQ-007 | `tests/api/test_evaluation_api.py::test_datos_base_l1` | `.venv/Scripts/python -m pytest tests/api/test_evaluation_api.py::test_datos_base_l1 -v` |
| 11 | CP-019 | REQ-005 | `tests/api/test_offers_api.py::test_oferta_cero_negativa_o_invalida_422` | `.venv/Scripts/python -m pytest tests/api/test_offers_api.py::test_oferta_cero_negativa_o_invalida_422 -v` |
| 12 | CP-020 | REQ-011 | `tests/api/test_tenders_api.py::test_los_datos_persisten_al_reiniciar_la_app` | `.venv/Scripts/python -m pytest tests/api/test_tenders_api.py::test_los_datos_persisten_al_reiniciar_la_app -v` |

Total: 12 pruebas automatizadas representativas (7 unitarias y 5 de API; mínimos de la práctica: ≥ 6 unitarias, ≥ 3 de API, ≥ 8 en total).

## Ejecutar todas las listadas

```
.venv/Scripts/python -m pytest -v \
  tests/unit/test_provider_rules.py::test_nombres_equivalentes_tienen_la_misma_clave \
  tests/unit/test_offer_rules.py::test_monto_sobre_el_presupuesto_se_rechaza \
  tests/unit/test_offer_rules.py::test_exactamente_en_el_cierre_se_rechaza \
  tests/unit/test_tender_rules.py::test_transiciones_invalidas \
  tests/unit/test_evaluation_rules.py::test_escenario_aislado_10_5_y_0_por_ciento \
  tests/unit/test_evaluation_rules.py::test_aprobador_por_rango \
  tests/unit/test_money.py::test_crc_a_usd_exige_tasa_positiva \
  tests/api/test_offers_api.py::test_proveedor_no_puede_ofertar_dos_veces \
  tests/api/test_tenders_api.py::test_codigo_duplicado_sin_distinguir_mayusculas_ni_espacios \
  tests/api/test_evaluation_api.py::test_datos_base_l1 \
  tests/api/test_offers_api.py::test_oferta_cero_negativa_o_invalida_422 \
  tests/api/test_tenders_api.py::test_los_datos_persisten_al_reiniciar_la_app
```

(En PowerShell, poner todo en una sola línea o usar el acento grave `` ` `` como continuación.)

## Notas

- Las pruebas E2E con Playwright (`tests/e2e/`) todavía no existen; CP-011 y CP-012 quedan como "pendiente (E2E)".
- Este documento describe las pruebas; las ejecuciones (RUN) y su evidencia (`04_Evidencias/EV-###`) se registran aparte.
