# Matriz de trazabilidad REQ ↔ CP ↔ pruebas

Fuente: `CLAUDE.md` (REQ-001 a REQ-014) y `docs/casos_prueba.md`. Los tests listados son los principales de cada CP; el detalle completo con node ids está en el catálogo.

| REQ | Descripción breve | CP | Pruebas automáticas principales | Modo |
|---|---|---|---|---|
| REQ-001 | Proveedores: crear/editar/listar; duplicados equivalentes | CP-001, CP-011 | `tests/unit/test_provider_rules.py::test_nombres_equivalentes_tienen_la_misma_clave`; `tests/api/test_providers_api.py::test_nombre_duplicado_equivalente_409`; `tests/unit/test_models.py::test_name_key_unica` | Auto (CP-001); manual + E2E pendiente (CP-011) |
| REQ-002 | Licitaciones: código único, título, presupuesto, cierre futuro | CP-009, CP-011 | `tests/api/test_tenders_api.py::test_codigo_duplicado_sin_distinguir_mayusculas_ni_espacios`, `::test_presupuesto_cero_negativo_o_invalido_422`, `::test_cierre_pasado_422` | Auto (CP-009); manual (CP-011) |
| REQ-003 | Estados: solo transiciones permitidas | CP-004, CP-014 | `tests/unit/test_tender_rules.py::test_transiciones_validas`, `::test_transiciones_invalidas`; `tests/api/test_tenders_api.py::test_no_se_reabre_una_cerrada_409` | Auto |
| REQ-004 | Vencimiento: ofertas solo en Publicadas y antes del cierre | CP-003, CP-011, CP-014 | `tests/unit/test_offer_rules.py::test_exactamente_en_el_cierre_se_rechaza`; `tests/api/test_offers_api.py::test_exactamente_en_el_cierre_se_rechaza` | Auto (CP-003, CP-014); manual (CP-011) |
| REQ-005 | Montos: oferta > 0 y ≤ presupuesto | CP-002, CP-019 | `tests/unit/test_offer_rules.py::test_montos_validos`, `::test_monto_sobre_el_presupuesto_se_rechaza`, `::test_monto_cero_o_negativo_se_rechaza`; `tests/api/test_offers_api.py::test_oferta_cero_negativa_o_invalida_422` | Auto |
| REQ-006 | Duplicados: una oferta por proveedor y licitación (también en BD) | CP-008 | `tests/api/test_offers_api.py::test_proveedor_no_puede_ofertar_dos_veces`, `::test_la_bd_tambien_rechaza_el_duplicado`; `tests/unit/test_models.py::test_oferta_unica_por_proveedor_y_licitacion` | Auto |
| REQ-007 | Mejor oferta, desempate, "Sin ofertas válidas" | CP-010, CP-012, CP-014 | `tests/api/test_evaluation_api.py::test_datos_base_l1`, `::test_empate_gana_la_registrada_primero`; `tests/api/test_evaluation_ui.py::test_sin_ofertas_muestra_sin_ofertas_validas` | Auto (CP-010, CP-014); manual (CP-012) |
| REQ-008 | Ahorro y clasificación | CP-005, CP-012 | `tests/unit/test_evaluation_rules.py::test_escenario_aislado_10_5_y_0_por_ciento`, `::test_clasificacion_en_la_frontera_del_diez_por_ciento` | Auto (CP-005); manual (CP-012) |
| REQ-009 | Aprobación por rangos configurables, semiabiertos | CP-006, CP-012 | `tests/unit/test_evaluation_rules.py::test_aprobador_por_rango`; `tests/api/test_evaluation_api.py::test_aprobador_en_las_fronteras_de_los_rangos` | Auto (CP-006); manual (CP-012) |
| REQ-010 | Moneda: solo CRC en BD, USD = CRC / tasa, tasa y fecha visibles | CP-007, CP-013 | `tests/unit/test_money.py::test_crc_a_usd_ejemplo_del_seed`, `::test_crc_a_usd_exige_tasa_positiva`; `tests/api/test_evaluation_ui.py::test_vista_usd_muestra_monto_tasa_y_fecha` | Auto |
| REQ-011 | Persistencia/API: errores verificables, mismas validaciones que la UI | CP-009, CP-020 | `tests/api/test_tenders_ui.py::test_crear_con_error_muestra_el_mismo_detalle_que_la_api`; `tests/api/test_tenders_api.py::test_los_datos_persisten_al_reiniciar_la_app`; `tests/api/test_offers_api.py::test_las_ofertas_persisten_al_reiniciar_la_app` | Auto |
| REQ-012 | Seguridad: nombre válido, escape de HTML, errores ocultos | CP-015, CP-016 | `tests/api/test_providers_api.py::test_nombre_invalido_422`; `tests/api/test_providers_ui.py::test_valores_renderizados_quedan_escapados`; `tests/api/test_errors_format.py::test_500_api_formato_generico_sin_traza` | Auto |
| REQ-013 | Usabilidad: ≥ 3 de 4 tareas sin ayuda con 2 personas ajenas | CP-017 | Manual | Manual |
| REQ-014 | Rendimiento: 5 VU, 30 s, p95 ≤ 1500 ms, error ≤ 5 % | CP-018 | Manual (herramienta de carga) | Manual |

## Verificación

Cada REQ tiene al menos un CP: REQ-001 (CP-001, CP-011), REQ-002 (CP-009, CP-011), REQ-003 (CP-004, CP-014), REQ-004 (CP-003, CP-011, CP-014), REQ-005 (CP-002, CP-019), REQ-006 (CP-008), REQ-007 (CP-010, CP-012, CP-014), REQ-008 (CP-005, CP-012), REQ-009 (CP-006, CP-012), REQ-010 (CP-007, CP-013), REQ-011 (CP-009, CP-020), REQ-012 (CP-015, CP-016), REQ-013 (CP-017), REQ-014 (CP-018). **Resultado: 14 de 14 REQ cubiertos.**

Inversa (CP → REQ): cada uno de los 20 CP cita al menos un REQ y todos aparecen en la matriz.

## Observaciones

- REQ-013 y REQ-014 solo tienen CP manuales (sin test automático).
- CP-011 y CP-012 no tienen aún prueba E2E; hay cobertura parcial en pruebas de API/UI sin navegador.
- Esta matriz refleja el diseño de casos; no registra ejecuciones (RUN) ni resultados.
