# Catálogo de casos de prueba (CP-001 a CP-020)

Sistema de Gestión de Licitaciones — ISW-622. Los resultados esperados salen de las reglas de negocio de `CLAUDE.md` (REQ-001 a REQ-014) y de `docs/contrato.md`, no del comportamiento del código.

- **Origen** de todos los casos: IA-asistida / mixta (diseño propuesto con IA y pendiente de revisión humana). Ficha generada en **IA-005**.
- **Revisor**: A COMPLETAR POR EL HUMANO en cada ficha. No se ha registrado ninguna ejecución (RUN) en este documento.
- **Test existente**: ruta y node id de pytest (`ruta::nombre`). Si el nodo está parametrizado, el node id sin corchetes ejecuta todas sus variantes. Comando general: `.venv/Scripts/python -m pytest <node id> -v`.
- Los tests de "API" y de "UI" usan `TestClient` (sin navegador); los E2E con Playwright (`tests/e2e/`) aún no existen y se marcan "pendiente (E2E)".

## Resumen

| CP | Tipo/nivel | REQ | Prioridad | Modo | Test existente |
|---|---|---|---|---|---|
| CP-001 | Unitaria | REQ-001 | Alta | Automático | Sí |
| CP-002 | Unitaria | REQ-005 | Alta | Automático | Sí |
| CP-003 | Unitaria | REQ-004 | Alta | Automático | Sí |
| CP-004 | Unitaria | REQ-003 | Alta | Automático | Sí |
| CP-005 | Unitaria | REQ-008 | Alta | Automático | Sí |
| CP-006 | Unitaria | REQ-009 | Alta | Automático | Sí |
| CP-007 | Unitaria | REQ-010 | Media | Automático | Sí |
| CP-008 | Integración/API | REQ-006 | Alta | Automático | Sí |
| CP-009 | Integración/API | REQ-002, REQ-011 | Alta | Automático | Sí |
| CP-010 | Integración/API | REQ-007 | Alta | Automático | Sí |
| CP-011 | Funcional | REQ-001, REQ-002, REQ-004 | Alta | Manual | Parcial; E2E pendiente |
| CP-012 | Funcional | REQ-007, REQ-008, REQ-009 | Alta | Manual | Parcial; E2E pendiente |
| CP-013 | Funcional | REQ-010 | Media | Automático (UI sin navegador) | Sí |
| CP-014 | Funcional | REQ-003, REQ-004, REQ-007 | Media | Automático (UI sin navegador) | Sí |
| CP-015 | Seguridad | REQ-012 | Alta | Automático | Sí |
| CP-016 | Seguridad | REQ-012 | Alta | Automático | Sí |
| CP-017 | Usabilidad | REQ-013 | Media | Manual | Manual |
| CP-018 | Rendimiento | REQ-014 | Media | Manual con herramienta de carga | Manual |
| CP-019 | Borde/negativo | REQ-005 | Alta | Automático | Sí |
| CP-020 | Borde/negativo | REQ-011 | Alta | Automático | Sí |

Cobertura por tipo (mínimos de la práctica): 7 unitarias (≥7), 3 integración/API (≥3), 4 funcionales (≥4), 2 seguridad (≥2), 1 usabilidad (≥1), 1 rendimiento (≥1), 2 de borde/negativo.

---

## CP-001
- **Título:** Nombre de proveedor equivalente a P1 se rechaza como duplicado
- **REQ:** REQ-001
- **Tipo/nivel:** Unitaria
- **Técnica:** Partición de equivalencia
- **Prioridad:** Alta
- **Precondiciones:** Existe P1 "Tecnología Norte S.A." (seed).
- **Entradas exactas:** nombre `"  tecnología   NORTE s.a. "` (espacios laterales, espacios internos repetidos, otras mayúsculas).
- **Pasos:**
  1. Normalizar el nombre de entrada (recortar, compactar espacios, ignorar mayúsculas).
  2. Compararlo con la clave de P1 "Tecnología Norte S.A.".
  3. Intentar crear el proveedor con ese nombre.
- **Resultado esperado:** Ambos nombres producen la misma clave y el alta se rechaza como duplicado (HTTP 409, `duplicado`); no se crea un segundo proveedor. (REQ-001: nombres equivalentes —recortar espacios, compactar espacios internos, sin distinguir mayúsculas— se rechazan como duplicados.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_provider_rules.py::test_nombres_equivalentes_tienen_la_misma_clave` (mismas claves con esta entrada exacta)
  - `tests/api/test_providers_api.py::test_nombre_duplicado_equivalente_409` (409 `duplicado`; incluye esta entrada)
  - `tests/unit/test_models.py::test_name_key_unica` (restricción UNIQUE en BD)
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-002 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-002
- **Título:** Oferta igual al presupuesto es válida; presupuesto + 0,01 se rechaza
- **REQ:** REQ-005
- **Tipo/nivel:** Unitaria
- **Técnica:** Valores límite
- **Prioridad:** Alta
- **Precondiciones:** Licitación con presupuesto CRC 1 000 000,00.
- **Entradas exactas:** oferta `"1000000.00"` (válida); oferta `"1000000.01"` (presupuesto + 0,01).
- **Pasos:**
  1. Validar el monto `1000000.00` contra el presupuesto `1000000.00`.
  2. Validar el monto `1000000.01` contra el mismo presupuesto.
- **Resultado esperado:** `1000000.00` se acepta (100 000 000 céntimos); `1000000.01` se rechaza con 422 `monto_excede_presupuesto`. (REQ-005: igual al presupuesto es válida; un céntimo por encima se rechaza.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_offer_rules.py::test_montos_validos` (incluye `1000000.00`)
  - `tests/unit/test_offer_rules.py::test_monto_sobre_el_presupuesto_se_rechaza` (incluye `1000000.01`)
  - `tests/api/test_offers_api.py::test_oferta_igual_al_presupuesto_es_valida` y `::test_oferta_un_centimo_sobre_el_presupuesto_422`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-051 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-003
- **Título:** Ofertas antes, exactamente en y después del cierre
- **REQ:** REQ-004
- **Tipo/nivel:** Unitaria
- **Técnica:** Valores límite
- **Prioridad:** Alta
- **Precondiciones:** Licitación Publicada con cierre en un instante `T`. Reloj controlado (FakeClock en las pruebas de API; la prueba unitaria pasa instantes fijos a la regla pura).
- **Entradas exactas:** ahora = `T − 1 s` (válida); ahora = `T` (rechazada); ahora = `T + 1 s` (rechazada).
- **Pasos:**
  1. Fijar el reloj en `T − 1 s` y ofertar.
  2. Fijar el reloj exactamente en `T` y ofertar.
  3. Fijar el reloj en `T + 1 s` y ofertar.
- **Resultado esperado:** En `T − 1 s` se acepta; en `T` y en `T + 1 s` se rechaza (`now >= cierre` rechaza) y la oferta no se guarda. (REQ-004.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_offer_rules.py::test_antes_del_cierre_se_acepta`, `::test_exactamente_en_el_cierre_se_rechaza`, `::test_despues_del_cierre_se_rechaza`
  - `tests/api/test_offers_api.py::test_un_segundo_antes_del_cierre_se_acepta`, `::test_exactamente_en_el_cierre_se_rechaza`, `::test_un_segundo_despues_del_cierre_se_rechaza` (con FakeClock)
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-051 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-004
- **Título:** Transiciones de estado de la licitación
- **REQ:** REQ-003
- **Tipo/nivel:** Unitaria
- **Técnica:** Transición de estados
- **Prioridad:** Alta
- **Precondiciones:** Ninguna (regla pura).
- **Entradas exactas:** Cerrada→Publicada y Publicada→Borrador (inválidas); Borrador→Publicada y Publicada→Cerrada (válidas).
- **Pasos:** Consultar y validar cada transición con `can_transition` / `check_transition`.
- **Resultado esperado:** Borrador→Publicada y Publicada→Cerrada se permiten; Cerrada→Publicada y Publicada→Borrador se rechazan con 409 `transicion_invalida`. (REQ-003: solo Borrador→Publicada, Borrador→Cerrada, Publicada→Cerrada; no volver a Borrador ni reabrir una Cerrada.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_tender_rules.py::test_transiciones_validas`
  - `tests/unit/test_tender_rules.py::test_transiciones_invalidas`
  - `tests/api/test_tenders_api.py::test_no_se_reabre_una_cerrada_409` (nivel API)
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-050 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-005
- **Título:** Ahorro y clasificación en el escenario aislado
- **REQ:** REQ-008
- **Tipo/nivel:** Unitaria
- **Técnica:** Valores límite / partición de equivalencia
- **Prioridad:** Alta
- **Precondiciones:** Presupuesto CRC 1 000 000,00.
- **Entradas exactas:** ofertas `900000.00`, `950000.00` y `1000000.00`.
- **Pasos:** Calcular ahorro % = ((presupuesto − oferta) / presupuesto) × 100 y clasificar cada oferta.
- **Resultado esperado:** 900 000 → 10 % "Conveniente"; 950 000 → 5 % "Aceptable"; 1 000 000 → 0 % "Válida sin ahorro". (REQ-008: ≥ 10 % Conveniente; > 0 y < 10 % Aceptable; 0 % Válida sin ahorro.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_evaluation_rules.py::test_escenario_aislado_10_5_y_0_por_ciento`
  - `tests/unit/test_evaluation_rules.py::test_clasificacion_en_la_frontera_del_diez_por_ciento` (límite 10 %)
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-052 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-006
- **Título:** Nivel de aprobación en las fronteras de los rangos
- **REQ:** REQ-009
- **Tipo/nivel:** Unitaria
- **Técnica:** Valores límite
- **Prioridad:** Alta
- **Precondiciones:** Rangos por defecto: Encargado de área 0,01–999 999,99; Gerencia 1 000 000,00–9 999 999,99; Junta Directiva ≥ 10 000 000,00.
- **Entradas exactas:** `999999.99`, `1000000.00`, `10000000.00`.
- **Pasos:** Determinar el aprobador para cada monto.
- **Resultado esperado:** 999 999,99 → Encargado de área; 1 000 000,00 → Gerencia; 10 000 000,00 → Junta Directiva. (REQ-009: intervalos semiabiertos [min, max).)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_evaluation_rules.py::test_aprobador_por_rango`
  - `tests/api/test_evaluation_api.py::test_aprobador_en_las_fronteras_de_los_rangos`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-052 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-007
- **Título:** Conversión CRC → USD y tasas inválidas
- **REQ:** REQ-010
- **Tipo/nivel:** Unitaria
- **Técnica:** Partición de equivalencia / valores límite
- **Prioridad:** Media
- **Precondiciones:** Ninguna (regla pura).
- **Entradas exactas:** monto `9000000.00` CRC con tasa `500.00` (válido); tasa `0` y tasa negativa (`-500`, `-1`) (inválidas).
- **Pasos:**
  1. Convertir `9000000.00` con tasa `500.00`.
  2. Intentar convertir con tasa `0` y con una tasa negativa.
- **Resultado esperado:** USD `18000.00`; las tasas `0` y negativa se rechazan con 422 `tasa_invalida`. (REQ-010: USD = CRC / (CRC por USD) con tasa > 0.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_money.py::test_crc_a_usd_ejemplo_del_seed` (900 000 000 céntimos / 500,00 = 18 000,00)
  - `tests/unit/test_money.py::test_crc_a_usd_exige_tasa_positiva` (0 y negativa)
  - `tests/unit/test_exchange_rate_rules.py::test_tasa_invalida_422` (rechazo al registrar la tasa)
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-001 / IA-003 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-008
- **Título:** Segunda oferta del mismo proveedor en la misma licitación
- **REQ:** REQ-006
- **Tipo/nivel:** Integración/API
- **Técnica:** Partición de equivalencia
- **Prioridad:** Alta
- **Precondiciones:** Seed cargado; sesión iniciada; P1 ya tiene una oferta en L1.
- **Entradas exactas:** `POST /api/tenders/{L1}/offers` con `provider_id` = P1 y un monto válido (por ejemplo `8000000.00`).
- **Pasos:**
  1. Iniciar sesión como operador.
  2. Enviar la segunda oferta de P1 a L1.
  3. Repetir saltándose la validación del service para comprobar la restricción de la BD.
- **Resultado esperado:** HTTP 409 con `{"error": "oferta_duplicada", "detalle": ...}`; la oferta original no cambia; la restricción UNIQUE (licitación, proveedor) de la BD también la rechaza. (REQ-006.)
- **Modo:** Automático
- **Test existente:**
  - `tests/api/test_offers_api.py::test_proveedor_no_puede_ofertar_dos_veces`
  - `tests/api/test_offers_api.py::test_la_bd_tambien_rechaza_el_duplicado`
  - `tests/unit/test_models.py::test_oferta_unica_por_proveedor_y_licitacion`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-051 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-009
- **Título:** La API rechaza código repetido, presupuesto 0 y cierre pasado con el formato de error
- **REQ:** REQ-002, REQ-011
- **Tipo/nivel:** Integración/API
- **Técnica:** Partición de equivalencia / tabla de decisión
- **Prioridad:** Alta
- **Precondiciones:** Seed cargado (existe `LIC-2026-001`); sesión iniciada.
- **Entradas exactas:** `POST /api/tenders` con (a) código `lic-2026-001` (otra capitalización); (b) presupuesto `"0"`; (c) cierre anterior al reloj actual. Mismos datos por el formulario de la UI.
- **Pasos:**
  1. Enviar cada solicitud por la API y leer estado y cuerpo.
  2. Enviar los mismos datos por la UI y comparar el detalle del error.
- **Resultado esperado:** (a) 409 `duplicado`; (b) 422 `monto_invalido`; (c) 422 de cierre pasado. Cuerpo exactamente `{"error", "detalle"}`. La UI rechaza lo mismo y muestra el mismo detalle. (REQ-002: código único sin distinguir mayúsculas, presupuesto > 0, cierre futuro; REQ-011: mismas validaciones en API y UI.)
- **Modo:** Automático
- **Test existente:**
  - `tests/api/test_tenders_api.py::test_codigo_duplicado_sin_distinguir_mayusculas_ni_espacios`
  - `tests/api/test_tenders_api.py::test_presupuesto_cero_negativo_o_invalido_422`
  - `tests/api/test_tenders_api.py::test_cierre_pasado_422`
  - `tests/api/test_tenders_ui.py::test_crear_con_error_muestra_el_mismo_detalle_que_la_api`
  - `tests/api/test_tenders_ui.py::test_crear_rechazos_por_ui`
  - `tests/api/test_errors_format.py::test_dominio_409_y_422` (formato de error)
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-050 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-010
- **Título:** Evaluación de L1 y desempate por orden de registro
- **REQ:** REQ-007
- **Tipo/nivel:** Integración/API
- **Técnica:** Tabla de decisión / valores límite (empate)
- **Prioridad:** Alta
- **Precondiciones:** Seed: L1 con ofertas P1 = 9 000 000,00 y P2 = 9 500 000,00. Para el empate, dos ofertas iguales registradas en instantes distintos.
- **Entradas exactas:** `GET /api/tenders/{L1}/evaluation`; escenario de empate con dos ofertas del mismo monto.
- **Pasos:**
  1. Evaluar L1 con los datos del seed.
  2. Crear un empate (mismo monto, registro en orden conocido) y evaluar.
- **Resultado esperado:** Mejor oferta = P1 (9 000 000,00). En el empate gana la registrada primero. (REQ-007: gana la menor oferta válida; en empate gana la registrada primero.)
- **Modo:** Automático
- **Test existente:**
  - `tests/api/test_evaluation_api.py::test_datos_base_l1`
  - `tests/api/test_evaluation_api.py::test_empate_gana_la_registrada_primero`
  - `tests/unit/test_evaluation_rules.py::test_empate_gana_la_registrada_primero`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-052 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-011
- **Título:** Flujo funcional: alta de proveedor, alta de licitación, publicar y ofertar
- **REQ:** REQ-001, REQ-002, REQ-004
- **Tipo/nivel:** Funcional
- **Técnica:** Caso de uso
- **Prioridad:** Alta
- **Precondiciones:** App en marcha con el seed; sesión de operador.
- **Entradas exactas:** proveedor "Insumos del Sur"; licitación con código nuevo, título no vacío, presupuesto `1000000.00` y cierre futuro; oferta `900000.00` del proveedor nuevo.
- **Pasos:**
  1. Ir a Proveedores → Nuevo, registrar el proveedor.
  2. Ir a Licitaciones → Nueva, registrar la licitación (queda en Borrador).
  3. Publicar la licitación.
  4. En el detalle, registrar la oferta del proveedor nuevo.
- **Resultado esperado:** El proveedor aparece en el listado; la licitación se crea en Borrador y pasa a Publicada; la oferta se registra y aparece en la tabla de ofertas. (REQ-001, REQ-002, REQ-004.)
- **Modo:** Manual (E2E Playwright pendiente)
- **Test existente:** Pendiente (E2E). Cobertura parcial por pasos, en UI sin navegador:
  - `tests/api/test_providers_ui.py::test_alta_correcta_redirige_al_listado_con_mensaje`
  - `tests/api/test_tenders_ui.py::test_crear_por_ui_redirige_al_detalle_en_borrador`
  - `tests/api/test_tenders_ui.py::test_publicar_cerrar_y_no_reabrir_por_ui`
  - `tests/api/test_offers_ui.py::test_registrar_oferta_por_ui`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-012
- **Título:** L1 muestra mejor oferta, ahorro, clasificación y aprobador
- **REQ:** REQ-007, REQ-008, REQ-009
- **Tipo/nivel:** Funcional
- **Técnica:** Caso de uso
- **Prioridad:** Alta
- **Precondiciones:** Seed cargado (L1 con P1 = 9 000 000,00 y P2 = 9 500 000,00); sesión iniciada.
- **Entradas exactas:** abrir el detalle de LIC-2026-001.
- **Pasos:** Iniciar sesión, abrir Licitaciones y entrar al detalle de LIC-2026-001.
- **Resultado esperado:** Mejor oferta P1; ahorro 10 %; "Conveniente"; aprobador Gerencia. (REQ-007, REQ-008 y REQ-009: presupuesto 10 000 000,00 y mejor oferta 9 000 000,00.)
- **Modo:** Manual (E2E Playwright pendiente)
- **Test existente:** Pendiente (E2E). Cobertura parcial sin navegador:
  - `tests/api/test_evaluation_ui.py::test_detalle_muestra_la_evaluacion_de_los_datos_base`
  - `tests/api/test_evaluation_api.py::test_datos_base_l1`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-013
- **Título:** Alternar a USD muestra P1 = USD 18 000,00 con tasa y fecha; la BD no cambia
- **REQ:** REQ-010
- **Tipo/nivel:** Funcional
- **Técnica:** Caso de uso
- **Prioridad:** Media
- **Precondiciones:** Seed con tasa CRC 500,00 por USD (fecha actual); sesión iniciada.
- **Entradas exactas:** detalle de LIC-2026-001 con vista `USD`.
- **Pasos:**
  1. Abrir el detalle de LIC-2026-001 en CRC.
  2. Alternar a USD.
  3. Comparar los importes guardados en la BD antes y después.
- **Resultado esperado:** Oferta de P1 = USD 18 000,00 con la tasa (500,00) y su fecha visibles; los importes CRC en la BD quedan idénticos. (REQ-010: alternar la vista no modifica la BD.)
- **Modo:** Automático (UI sin navegador); versión E2E pendiente
- **Test existente:**
  - `tests/api/test_evaluation_ui.py::test_vista_usd_muestra_monto_tasa_y_fecha`
  - `tests/api/test_evaluation_ui.py::test_la_vista_de_evaluacion_no_modifica_la_bd`
  - `tests/api/test_evaluation_api.py::test_alternar_moneda_no_modifica_la_bd`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-052 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-014
- **Título:** Ofertas en Borrador/Cerrada rechazadas; sin ofertas se muestra "Sin ofertas válidas"
- **REQ:** REQ-003, REQ-004, REQ-007
- **Tipo/nivel:** Funcional
- **Técnica:** Transición de estados / tabla de decisión
- **Prioridad:** Media
- **Precondiciones:** Una licitación en Borrador, una Cerrada y una Publicada sin ofertas.
- **Entradas exactas:** oferta válida en monto sobre la licitación en Borrador y sobre la Cerrada; abrir el detalle de una licitación sin ofertas.
- **Pasos:**
  1. Intentar ofertar en la licitación en Borrador.
  2. Intentar ofertar en la licitación Cerrada.
  3. Abrir el detalle de una licitación sin ofertas.
- **Resultado esperado:** Ambas ofertas se rechazan (solo se aceptan ofertas en licitaciones Publicadas) y no se guardan; el detalle sin ofertas muestra "Sin ofertas válidas". (REQ-003, REQ-004, REQ-007.)
- **Modo:** Automático (API/UI sin navegador); versión E2E pendiente
- **Test existente:**
  - `tests/api/test_offers_api.py::test_licitacion_en_borrador_no_acepta_ofertas`
  - `tests/api/test_offers_api.py::test_licitacion_cerrada_no_acepta_ofertas`
  - `tests/api/test_offers_ui.py::test_licitacion_cerrada_no_acepta_ofertas_por_ui`
  - `tests/api/test_evaluation_ui.py::test_sin_ofertas_muestra_sin_ofertas_validas`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-051 / IA-052 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-015
- **Título:** Nombre de proveedor con `<script>` o símbolos no permitidos
- **REQ:** REQ-012
- **Tipo/nivel:** Seguridad
- **Técnica:** Partición de equivalencia / pruebas de inyección
- **Prioridad:** Alta
- **Precondiciones:** Sesión iniciada.
- **Entradas exactas:** nombres `<script>alert(1)</script>`, `Acme & Co`, `Nombre; DROP TABLE`, `Acme 😀`.
- **Pasos:**
  1. Intentar crear un proveedor con cada nombre (API y formulario de la UI).
  2. Revisar la respuesta renderizada y el listado.
- **Resultado esperado:** Se rechaza con 422 `validacion_nombre` (solo letras con tildes y ñ, números, espacios, punto, coma y paréntesis); no se guarda nada; el valor mostrado en el formulario queda escapado y no se ejecuta ningún script. (REQ-012.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_provider_rules.py::test_nombre_con_caracteres_no_permitidos_se_rechaza`
  - `tests/api/test_providers_api.py::test_nombre_invalido_422`
  - `tests/api/test_providers_ui.py::test_alta_con_error_se_muestra_en_error_message`
  - `tests/api/test_providers_ui.py::test_valores_renderizados_quedan_escapados`
  - `tests/api/test_providers_ui.py::test_nombre_guardado_se_escapa_en_listado_y_edicion`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-002 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-016
- **Título:** Ruta/ID inexistente y error forzado sin trazas, rutas ni credenciales
- **REQ:** REQ-012
- **Tipo/nivel:** Seguridad
- **Técnica:** Pruebas negativas / manejo de errores
- **Prioridad:** Alta
- **Precondiciones:** App con rutas de prueba que lanzan un error interno con un texto "secreto" (fixture `boom_app`).
- **Entradas exactas:** `GET /api/no-existe`; `GET /api/providers/99999`; ruta que provoca un error 500 (API y UI).
- **Pasos:** Solicitar cada ruta y leer el cuerpo completo de la respuesta.
- **Resultado esperado:** 404 `no_encontrado` para lo inexistente; 500 `error_interno` genérico para el error forzado, en formato `{"error","detalle"}` (API) o página genérica (UI). Ninguna respuesta contiene `Traceback`, nombres de archivo `.py`, rutas ni credenciales. (REQ-012: ocultar errores internos.)
- **Modo:** Automático
- **Test existente:**
  - `tests/api/test_errors_format.py::test_500_api_formato_generico_sin_traza`
  - `tests/api/test_errors_format.py::test_500_ui_pagina_generica_sin_traza`
  - `tests/api/test_errors_format.py::test_404_api`
  - `tests/api/test_providers_api.py::test_error_no_expone_trazas_ni_rutas`
  - `tests/api/test_offers_ui.py::test_oferta_inexistente_404_en_ui`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-001 / IA-002 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-017
- **Título:** Prueba de usabilidad con dos personas ajenas
- **REQ:** REQ-013
- **Tipo/nivel:** Usabilidad
- **Técnica:** Prueba con usuarios (exploratoria guiada)
- **Prioridad:** Media
- **Precondiciones:** App con el seed; dos personas que no participaron en el desarrollo; sin explicación previa de la interfaz; cronómetro y hoja de observación.
- **Entradas exactas:** 4 tareas por persona, por ejemplo: (1) iniciar sesión, (2) registrar un proveedor, (3) abrir una licitación Publicada, (4) registrar una oferta con ese proveedor.
- **Pasos:** Entregar el enunciado de las 4 tareas, observar sin intervenir, anotar éxito/fracaso, ayuda solicitada y tiempo por tarea.
- **Resultado esperado:** Al menos 3 de las 4 tareas se completan sin ayuda (REQ-013).
- **Modo:** Manual
- **Test existente:** Manual
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-018
- **Título:** Rendimiento del listado: 5 usuarios virtuales durante 30 s
- **REQ:** REQ-014
- **Tipo/nivel:** Rendimiento
- **Técnica:** Prueba de carga
- **Prioridad:** Media
- **Precondiciones:** App local en marcha con el seed; sesión válida (cookie) para las solicitudes; herramienta de carga (por ejemplo k6, Locust o JMeter) instalada.
- **Entradas exactas:** `GET /api/tenders` (listado), 5 usuarios virtuales concurrentes, 30 s de duración.
- **Pasos:** Configurar el escenario, ejecutarlo contra la app local y guardar el reporte como evidencia (`04_Evidencias/EV-###`).
- **Resultado esperado:** p95 ≤ 1500 ms y tasa de error ≤ 5 % (REQ-014).
- **Modo:** Manual con herramienta de carga
- **Test existente:** Manual
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-019
- **Título:** Oferta de 0 y de monto negativo se rechazan
- **REQ:** REQ-005
- **Tipo/nivel:** Borde/negativo (unitaria y API)
- **Técnica:** Valores límite
- **Prioridad:** Alta
- **Precondiciones:** Licitación Publicada con presupuesto CRC 1 000 000,00; sesión iniciada para la prueba de API.
- **Entradas exactas:** monto `"0"`, `"0.00"`, `"-0.01"`, `"-1000000.00"`.
- **Pasos:** Enviar cada monto como oferta (regla pura y `POST` a la API).
- **Resultado esperado:** Se rechaza con 422 y no se guarda ninguna oferta. (REQ-005: oferta > 0; cero y negativo se rechazan.)
- **Modo:** Automático
- **Test existente:**
  - `tests/unit/test_offer_rules.py::test_monto_cero_o_negativo_se_rechaza`
  - `tests/api/test_offers_api.py::test_oferta_cero_negativa_o_invalida_422`
  - `tests/unit/test_models.py::test_oferta_monto_debe_ser_positivo` (CHECK en BD)
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-051 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO

## CP-020
- **Título:** Persistencia tras reiniciar la app
- **REQ:** REQ-011
- **Tipo/nivel:** Borde/negativo (persistencia)
- **Técnica:** Caso de uso / pruebas de estado
- **Prioridad:** Alta
- **Precondiciones:** BD en archivo; sesión iniciada.
- **Entradas exactas:** crear un proveedor, una licitación y una oferta; reiniciar la aplicación (nueva instancia sobre la misma BD).
- **Pasos:**
  1. Crear proveedor, licitación y oferta.
  2. Detener y volver a crear la aplicación con la misma BD.
  3. Consultar los tres registros.
- **Resultado esperado:** El proveedor, la licitación y la oferta siguen presentes con los mismos datos. (REQ-011: los datos persisten al reiniciar.)
- **Modo:** Automático
- **Brecha conocida:** los tests automáticos verifican la licitación (publicada, presupuesto) y la oferta (más el conteo de ofertas de L1) tras reiniciar; no hay un test que cree un proveedor nuevo y lo relea tras reiniciar (el proveedor solo se comprueba de forma indirecta como parte de la oferta). Cubrirlo queda pendiente o se verifica manualmente en la ejecución (RUN).
- **Test existente:**
  - `tests/api/test_tenders_api.py::test_los_datos_persisten_al_reiniciar_la_app`
  - `tests/api/test_offers_api.py::test_las_ofertas_persisten_al_reiniciar_la_app`
  - `tests/api/test_evaluation_api.py::test_la_evaluacion_persiste_al_reiniciar_la_app`
- **Origen:** IA-asistida / mixta
- **IA ID:** IA-050 / IA-051 / IA-052 (tests), IA-005 (ficha)
- **Revisor:** A COMPLETAR POR EL HUMANO
