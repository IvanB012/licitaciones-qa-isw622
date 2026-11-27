"""Ejecuta CP automáticos con pytest sobre el commit actual y escribe la evidencia en 04_Evidencias/.

Uso:  python ejecutar_cp.py <repo> <salida_json> [CP-### | SUITE | RUN-### ...]   (sin ids ejecuta todos; volver a ejecutar un CP sobrescribe su evidencia)
Los veredictos salen de la salida real de pytest: código de retorno, cada test pedido en PASSED y ninguno en FAILED.
"""
import copy
import datetime
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(sys.argv[1])
RESUMEN = Path(sys.argv[2])
OUT = REPO / "04_Evidencias"
OUT.mkdir(exist_ok=True)

U = "tests/unit/test_offer_rules.py"
A = "tests/api/test_offers_api.py"
M = "tests/unit/test_models.py"
TR = "tests/unit/test_tender_rules.py"
ER = "tests/unit/test_evaluation_rules.py"
EA = "tests/api/test_evaluation_api.py"
TA = "tests/api/test_tenders_api.py"
TUI = "tests/api/test_tenders_ui.py"
FE = "tests/api/test_errors_format.py"

CASOS = [
    {
        "run": "RUN-052", "ev": "EV-056", "cp": "CP-003", "req": "REQ-004", "archivo": "EV-056_CP-003_cierre_antes_exacto_despues.txt",
        "titulo": "Ofertas antes, exactamente en y después del cierre",
        "entradas": "ahora = T-1 s (válida); ahora = T (rechazada); ahora = T+1 s (rechazada). Reloj controlado con FakeClock.",
        "esperado": "En T-1 s se acepta; en T y en T+1 s se rechaza (now >= cierre rechaza) con 409 licitacion_vencida y la oferta no se guarda. (REQ-004)",
        "nodos": [
            f"{U}::test_antes_del_cierre_se_acepta", f"{U}::test_exactamente_en_el_cierre_se_rechaza", f"{U}::test_despues_del_cierre_se_rechaza",
            f"{A}::test_un_segundo_antes_del_cierre_se_acepta", f"{A}::test_exactamente_en_el_cierre_se_rechaza", f"{A}::test_un_segundo_despues_del_cierre_se_rechaza",
            f"{A}::test_oferta_rechazada_por_plazo_no_se_guarda",
        ],
        "nota": "El último test no figura en la ficha del catálogo. Se agregó porque el resultado esperado exige que la oferta rechazada NO se guarde y los tests listados solo comprueban el código de error.",
    },
    {
        "run": "RUN-053", "ev": "EV-057", "cp": "CP-002", "req": "REQ-005", "archivo": "EV-057_CP-002_monto_igual_y_sobre_presupuesto.txt",
        "titulo": "Oferta igual al presupuesto es válida; presupuesto + 0,01 se rechaza",
        "entradas": "presupuesto CRC 1 000 000,00; oferta \"1000000.00\" (válida) y oferta \"1000000.01\" (presupuesto + 0,01).",
        "esperado": "1000000.00 se acepta (100 000 000 céntimos); 1000000.01 se rechaza con 422 monto_excede_presupuesto. (REQ-005)",
        "nodos": [
            f"{U}::test_montos_validos", f"{U}::test_monto_sobre_el_presupuesto_se_rechaza",
            f"{A}::test_oferta_igual_al_presupuesto_es_valida", f"{A}::test_oferta_un_centimo_sobre_el_presupuesto_422",
        ],
    },
    {
        "run": "RUN-054", "ev": "EV-058", "cp": "CP-019", "req": "REQ-005", "archivo": "EV-058_CP-019_monto_cero_y_negativo.txt",
        "titulo": "Oferta de 0 y de monto negativo se rechazan",
        "entradas": "presupuesto CRC 1 000 000,00; montos \"0\", \"0.00\", \"-0.01\" y \"-1000000.00\" (regla pura); la API se prueba con 0, 0.00 y negativos.",
        "esperado": "Se rechaza con 422 y no se guarda ninguna oferta (también la restricción CHECK de la BD). (REQ-005: oferta > 0)",
        "nodos": [
            f"{U}::test_monto_cero_o_negativo_se_rechaza", f"{A}::test_oferta_cero_negativa_o_invalida_422", f"{M}::test_oferta_monto_debe_ser_positivo",
            "tests/api/test_offers_ui.py::test_montos_rechazados_por_ui_no_se_guardan",
        ],
        "nota": "El último test no figura en la ficha del catálogo. Se agregó porque el resultado esperado exige que NO se guarde ninguna oferta (comprueba que el conteo de ofertas no cambia tras enviar 0 y un negativo por el formulario). "
        "Además, los valores literales -0.01 y -1000000.00 se prueban en la regla pura (unitaria); en la API los negativos probados son -1 y -900000.00 (misma clase de equivalencia).",
    },
    {
        "run": "RUN-055", "ev": "EV-059", "cp": "CP-004", "req": "REQ-003", "archivo": "EV-059_CP-004_transiciones_de_estado.txt",
        "titulo": "Transiciones de estado de la licitación",
        "entradas": "Borrador->Publicada y Publicada->Cerrada (válidas); Cerrada->Publicada y Publicada->Borrador (inválidas). También Borrador->Cerrada (válida).",
        "esperado": "Borrador->Publicada, Borrador->Cerrada y Publicada->Cerrada se permiten; Cerrada->Publicada y Publicada->Borrador se rechazan con 409 transicion_invalida. (REQ-003)",
        "nodos": [f"{TR}::test_transiciones_validas", f"{TR}::test_transiciones_invalidas", f"{TA}::test_no_se_reabre_una_cerrada_409"],
    },
    {
        "run": "RUN-056", "ev": "EV-060", "cp": "CP-005", "req": "REQ-008", "archivo": "EV-060_CP-005_ahorro_y_clasificacion.txt",
        "titulo": "Ahorro y clasificación en el escenario aislado",
        "entradas": "presupuesto CRC 1 000 000,00; ofertas 900000.00, 950000.00 y 1000000.00.",
        "esperado": "900 000 -> 10 % Conveniente; 950 000 -> 5 % Aceptable; 1 000 000 -> 0 % Válida sin ahorro. (REQ-008: >= 10 % Conveniente; > 0 y < 10 % Aceptable; 0 % Válida sin ahorro)",
        "nodos": [f"{ER}::test_escenario_aislado_10_5_y_0_por_ciento", f"{ER}::test_clasificacion_en_la_frontera_del_diez_por_ciento"],
    },
    {
        "run": "RUN-057", "ev": "EV-061", "cp": "CP-006", "req": "REQ-009", "archivo": "EV-061_CP-006_aprobador_fronteras.txt",
        "titulo": "Nivel de aprobación en las fronteras de los rangos",
        "entradas": "montos 999999.99, 1000000.00 y 10000000.00 con los rangos por defecto.",
        "esperado": "999 999,99 -> Encargado de área; 1 000 000,00 -> Gerencia; 10 000 000,00 -> Junta Directiva. (REQ-009: intervalos semiabiertos [min, max))",
        "nodos": [f"{ER}::test_aprobador_por_rango", f"{EA}::test_aprobador_en_las_fronteras_de_los_rangos"],
    },
    {
        "run": "RUN-058", "ev": "EV-062", "cp": "CP-008", "req": "REQ-006", "archivo": "EV-062_CP-008_oferta_duplicada.txt",
        "titulo": "Segunda oferta del mismo proveedor en la misma licitación",
        "entradas": "POST /api/tenders/{L1}/offers con provider_id = P1 (que ya ofertó en L1) y monto 8000000.00; repetido saltándose el chequeo del service.",
        "esperado": "HTTP 409 {\"error\": \"oferta_duplicada\", \"detalle\": ...}; la oferta original no cambia; la restricción UNIQUE (licitación, proveedor) de la BD también la rechaza. (REQ-006)",
        "nodos": [
            f"{A}::test_proveedor_no_puede_ofertar_dos_veces", f"{A}::test_la_bd_tambien_rechaza_el_duplicado",
            f"{M}::test_oferta_unica_por_proveedor_y_licitacion", f"{A}::test_el_duplicado_no_altera_la_oferta_original",
        ],
        "nota": "El último test no figura en la ficha del catálogo. Se agregó porque el resultado esperado exige que la oferta original no cambie y los tres tests listados no lo comprueban.",
    },
    {
        "run": "RUN-059", "ev": "EV-063", "cp": "CP-009", "req": "REQ-002, REQ-011", "archivo": "EV-063_CP-009_licitacion_rechazos_api_ui.txt",
        "titulo": "La API rechaza código repetido, presupuesto 0 y cierre pasado con el formato de error",
        "entradas": "POST /api/tenders con (a) código lic-2026-001 (otra capitalización); (b) presupuesto \"0\"; (c) cierre anterior al reloj. Mismos datos por el formulario de la UI.",
        "esperado": "(a) 409 duplicado; (b) 422 monto_invalido; (c) 422 cierre_no_futuro. Cuerpo exactamente {error, detalle}. La UI rechaza lo mismo y muestra el mismo detalle. (REQ-002 y REQ-011)",
        "nodos": [
            f"{TA}::test_codigo_duplicado_sin_distinguir_mayusculas_ni_espacios", f"{TA}::test_presupuesto_cero_negativo_o_invalido_422", f"{TA}::test_cierre_pasado_422",
            f"{TUI}::test_crear_con_error_muestra_el_mismo_detalle_que_la_api", f"{TUI}::test_crear_rechazos_por_ui", f"{FE}::test_dominio_409_y_422",
        ],
        "nota": "La comparación literal del texto de error entre API y UI (test_crear_con_error_muestra_el_mismo_detalle_que_la_api) se hace con el caso (b), presupuesto 0. En los casos (a) y (c) la UI se verifica por estado HTTP y fragmento del mensaje.",
    },
    {
        "run": "RUN-060", "ev": "EV-064", "cp": "CP-010", "req": "REQ-007", "archivo": "EV-064_CP-010_evaluacion_y_empate.txt",
        "titulo": "Evaluación de L1 y desempate por orden de registro",
        "entradas": "GET /api/tenders/{L1}/evaluation con el seed (P1 = 9 000 000,00; P2 = 9 500 000,00); escenario de empate con dos ofertas del mismo monto registradas en instantes distintos.",
        "esperado": "Mejor oferta = P1 (9 000 000,00). En el empate gana la registrada primero. (REQ-007)",
        "nodos": [f"{EA}::test_datos_base_l1", f"{EA}::test_empate_gana_la_registrada_primero", f"{ER}::test_empate_gana_la_registrada_primero"],
    },
    # ---- Casos de Iván (RUN-001 a RUN-049 / EV-001 a EV-049). Ejecutar con ids: SUITE CP-001 CP-007 CP-013 CP-014 CP-020 ----
    {
        "run": "RUN-001", "ev": "EV-001", "cp": "SUITE", "req": "REQ-001 a REQ-012 (todos los automáticos)", "archivo": "EV-001_pytest_suite_qa-build-1.txt",
        "titulo": "Suite completa de pytest sobre el build qa-build-1",
        "entradas": "pytest -v sobre todo el directorio tests/ (sin ids de prueba), con una BD SQLite temporal por prueba y sin acceso a la red.",
        "esperado": "Todas las pruebas pasan: 928 passed, 0 failed, 0 errors. (CLAUDE.md: commitear solo con pytest en verde; resultado esperado de cada prueba = reglas REQ)",
        "nodos": [],
        "esperado_passed": 928,
    },
    {
        "run": "RUN-002", "ev": "EV-002", "cp": "CP-001", "req": "REQ-001", "archivo": "EV-002_CP-001_proveedor_duplicado_equivalente.txt",
        "titulo": "Nombre de proveedor equivalente a P1 se rechaza como duplicado",
        "entradas": "P1 \"Tecnología Norte S.A.\" (seed); nombre \"  tecnología   NORTE s.a. \" (espacios laterales, espacios internos repetidos, otras mayúsculas).",
        "esperado": "Ambos nombres producen la misma clave y el alta se rechaza como duplicado (409 duplicado); no se crea un segundo proveedor (la BD también lo impide con UNIQUE). (REQ-001)",
        "nodos": [
            "tests/unit/test_provider_rules.py::test_nombres_equivalentes_tienen_la_misma_clave",
            "tests/api/test_providers_api.py::test_nombre_duplicado_equivalente_409",
            f"{M}::test_name_key_unica",
        ],
        "nota": "Ejecuta los 3 tests de la ficha, sin añadidos. Límite: ningún test cuenta los proveedores tras el rechazo; \"no se crea un segundo proveedor\" se sustenta en el 409 de la API y en el rechazo UNIQUE de la BD (test_name_key_unica).",
    },
    {
        "run": "RUN-003", "ev": "EV-003", "cp": "CP-007", "req": "REQ-010", "archivo": "EV-003_CP-007_conversion_usd_y_tasas_invalidas.txt",
        "titulo": "Conversión CRC -> USD y tasas inválidas",
        "entradas": "9000000.00 CRC con tasa 500.00 (válido); tasa 0 y tasas negativas (inválidas).",
        "esperado": "USD 18000.00; las tasas 0 y negativas se rechazan con 422 tasa_invalida. (REQ-010: USD = CRC / (CRC por USD) con tasa > 0)",
        "nodos": [
            "tests/unit/test_money.py::test_crc_a_usd_ejemplo_del_seed",
            "tests/unit/test_money.py::test_crc_a_usd_exige_tasa_positiva",
            "tests/unit/test_exchange_rate_rules.py::test_tasa_invalida_422",
        ],
        "nota": "Ejecuta los 3 tests de la ficha, sin añadidos.",
    },
    {
        "run": "RUN-004", "ev": "EV-004", "cp": "CP-013", "req": "REQ-010", "archivo": "EV-004_CP-013_vista_usd_sin_modificar_bd.txt",
        "titulo": "Alternar a USD muestra P1 = USD 18 000,00 con tasa y fecha; la BD no cambia",
        "entradas": "Detalle de LIC-2026-001 (seed: tasa CRC 500,00 por USD con fecha actual) en vista CRC y en vista USD; importes CRC de la BD antes y después.",
        "esperado": "La oferta de P1 se muestra como USD 18 000,00 con la tasa (500,00) y su fecha visibles; los importes CRC guardados quedan idénticos. (REQ-010: alternar la vista no modifica la BD)",
        "nodos": [
            "tests/api/test_evaluation_ui.py::test_vista_usd_muestra_monto_tasa_y_fecha",
            "tests/api/test_evaluation_ui.py::test_la_vista_de_evaluacion_no_modifica_la_bd",
            f"{EA}::test_alternar_moneda_no_modifica_la_bd",
        ],
        "nota": "Ejecuta los 3 tests de la ficha, sin añadidos. Es UI renderizada en servidor con TestClient (sin navegador); la versión E2E sigue pendiente.",
    },
    {
        "run": "RUN-005", "ev": "EV-005", "cp": "CP-014", "req": "REQ-003, REQ-004, REQ-007", "archivo": "EV-005_CP-014_borrador_cerrada_y_sin_ofertas.txt",
        "titulo": "Ofertas en Borrador/Cerrada rechazadas; sin ofertas se muestra \"Sin ofertas válidas\"",
        "entradas": "Oferta con monto válido sobre una licitación en Borrador y sobre una Cerrada; detalle de una licitación sin ofertas.",
        "esperado": "Ambas ofertas se rechazan (solo se aceptan ofertas en licitaciones Publicadas) con 409 licitacion_no_publicada y no se guardan; el detalle sin ofertas muestra \"Sin ofertas válidas\". (REQ-003, REQ-004, REQ-007)",
        "nodos": [
            f"{A}::test_licitacion_en_borrador_no_acepta_ofertas",
            f"{A}::test_licitacion_cerrada_no_acepta_ofertas",
            "tests/api/test_offers_ui.py::test_licitacion_cerrada_no_acepta_ofertas_por_ui",
            "tests/api/test_evaluation_ui.py::test_sin_ofertas_muestra_sin_ofertas_validas",
        ],
        "nota": "Ejecuta los 4 tests de la ficha, sin añadidos. Límite: \"no se guardan\" solo se comprueba con conteo para la licitación Cerrada por UI (test_licitacion_cerrada_no_acepta_ofertas_por_ui); para Borrador solo se comprueba el 409. Es UI/API sin navegador; la versión E2E sigue pendiente.",
    },
    {
        "run": "RUN-006", "ev": "EV-006", "cp": "CP-020", "req": "REQ-011", "archivo": "EV-006_CP-020_persistencia_al_reiniciar.txt",
        "titulo": "Persistencia tras reiniciar la app",
        "entradas": "Licitación creada y publicada, oferta registrada y evaluación de L1; la aplicación se vuelve a crear (motor nuevo) sobre la misma BD en archivo y se consultan los registros.",
        "esperado": "La licitación, la oferta y la evaluación siguen presentes con los mismos datos tras reiniciar. (REQ-011: los datos persisten al reiniciar)",
        "nodos": [
            f"{TA}::test_los_datos_persisten_al_reiniciar_la_app",
            "tests/api/test_offers_api.py::test_las_ofertas_persisten_al_reiniciar_la_app",
            f"{EA}::test_la_evaluacion_persiste_al_reiniciar_la_app",
        ],
        "nota": "Ejecuta los 3 tests de la ficha, sin añadidos. BRECHA CONOCIDA: ningún test crea un proveedor nuevo y lo vuelve a leer tras reiniciar (el proveedor solo se comprueba de forma indirecta, como parte de la oferta). Se cierra con el E2E o con una verificación manual.",
    },
]


# ---- BUG-001 (defecto controlado): RUN-007 a RUN-010. Se derivan de los casos de Ian SIN modificarlos y se seleccionan por id de RUN ----
def _derivar(cp, run, ev, archivo, **cambios):
    base = copy.deepcopy(next(c for c in CASOS if c["cp"] == cp and c["run"].startswith("RUN-05")))
    base.update({"run": run, "ev": ev, "archivo": archivo, "sel": run}, **cambios)
    return base


CASOS += [
    _derivar(
        "CP-003", "RUN-007", "EV-007", "EV-007_BUG-001_CP-003_falla_con_defecto.txt",
        titulo="BUG-001 - CP-003 con el defecto introducido: oferta exactamente en el cierre",
        nota="EJECUCIÓN SOBRE EL COMMIT DEL DEFECTO (tag bug-001-defecto): en app/rules/offers.py la comparación `now >= closes_at` se cambió a `now > closes_at`. "
        "Se espera que FALLEN los tests que prueban el instante exacto del cierre. No se corrigió nada antes de ejecutar.",
    ),
    _derivar(
        "CP-003", "RUN-008", "EV-008", "EV-008_BUG-001_CP-003_retest_con_fix.txt",
        titulo="BUG-001 - CP-003 retest sobre el commit del fix",
        nota="RETEST sobre el commit de la corrección (tag bug-001-fix): la comparación vuelve a `now >= closes_at`. Mismos tests que RUN-007.",
    ),
    _derivar(
        "CP-002", "RUN-009", "EV-009", "EV-009_BUG-001_CP-002_regresion.txt",
        titulo="BUG-001 - CP-002 regresión sobre el commit del fix: monto igual al presupuesto y presupuesto + 0,01",
        nota="REGRESIÓN sobre el commit de la corrección (tag bug-001-fix): CP-002 no debe verse afectado por el arreglo del cierre.",
    ),
    _derivar(
        "CP-019", "RUN-010", "EV-010", "EV-010_BUG-001_CP-019_regresion.txt",
        titulo="BUG-001 - CP-019 regresión sobre el commit del fix: oferta de 0 y de monto negativo",
        nota="REGRESIÓN sobre el commit de la corrección (tag bug-001-fix): CP-019 no debe verse afectado por el arreglo del cierre.",
    ),
]


# ---- E2E (Playwright): RUN-011 a RUN-014. No existen en el tag qa-build-1: se ejecutan en HEAD y se demuestra que app/seeds/requirements son los del tag ----
E2E = "tests/e2e/test_flujos_e2e.py"
CASOS += [
    {
        "run": "RUN-011", "ev": "EV-011", "cp": "CP-011", "sel": "RUN-011", "e2e": True, "req": "REQ-001, REQ-002, REQ-004",
        "archivo": "EV-011_CP-011_E2E_alta_publicar_y_ofertar.txt",
        "titulo": "E2E: alta de proveedor, alta de licitación, publicar y ofertar",
        "entradas": "Navegador Chromium headless contra la app real (uvicorn, BD temporal con el seed). Login como admin; proveedor \"Insumos del Sur E2E\"; licitación LIC-E2E-001 (presupuesto 1000000.00, cierre en 3 días); publicar; oferta de 900000.00 con ese proveedor.",
        "esperado": "El proveedor aparece en el listado; la licitación se crea en Borrador y pasa a Publicada; la oferta se registra y aparece en la tabla de ofertas (mejor oferta, ahorro 10 %). (REQ-001, REQ-002, REQ-004)",
        "nodos": [f"{E2E}::test_flujo_alta_proveedor_licitacion_publicar_y_ofertar"],
        "capturas": [f"EV-011_CP-011_{n}.png" for n in ("01_login_panel", "02_proveedor_creado", "03_licitacion_borrador", "04_licitacion_publicada", "05_oferta_registrada")],
    },
    {
        "run": "RUN-012", "ev": "EV-012", "cp": "CP-012", "sel": "RUN-012", "e2e": True, "req": "REQ-007, REQ-008, REQ-009",
        "archivo": "EV-012_CP-012_E2E_evaluacion_l1.txt",
        "titulo": "E2E: L1 muestra mejor oferta, ahorro, clasificación y aprobador",
        "entradas": "Navegador Chromium headless contra la app real con el seed; login como admin; detalle de LIC-2026-001 (presupuesto 10 000 000,00; ofertas P1 = 9 000 000,00 y P2 = 9 500 000,00).",
        "esperado": "Mejor oferta P1 (Tecnología Norte S.A.); ahorro 10 %; Conveniente; aprueba Gerencia. (REQ-007, REQ-008, REQ-009)",
        "nodos": [f"{E2E}::test_detalle_de_l1_muestra_mejor_oferta_ahorro_clasificacion_y_aprobador"],
        "capturas": ["EV-012_CP-012_01_detalle_l1_evaluacion.png"],
    },
    {
        "run": "RUN-013", "ev": "EV-013", "cp": "CP-013", "sel": "RUN-013", "e2e": True, "req": "REQ-010",
        "archivo": "EV-013_CP-013_E2E_vista_usd.txt",
        "titulo": "E2E: alternar a USD muestra USD 18 000,00 con tasa y fecha; los importes no cambian",
        "entradas": "Navegador Chromium headless contra la app real con el seed (tasa CRC 500,00 por USD con fecha actual); detalle de LIC-2026-001 en CRC, luego USD, luego CRC; importes guardados leídos por la API antes y después.",
        "esperado": "La oferta de P1 se muestra como $18 000,00 (y la de P2 como $19 000,00) con la tasa y su fecha visibles; al volver a CRC los montos son los mismos; los importes CRC guardados no cambian. (REQ-010)",
        "nodos": [f"{E2E}::test_vista_usd_de_l1_muestra_tasa_y_fecha_y_no_cambia_los_importes"],
        "capturas": [f"EV-013_CP-013_{n}.png" for n in ("01_l1_en_crc", "02_l1_en_usd", "03_l1_vuelve_a_crc")],
    },
    {
        "run": "RUN-014", "ev": "EV-014", "cp": "CP-020", "sel": "RUN-014", "e2e": True, "req": "REQ-011",
        "archivo": "EV-014_CP-020_E2E_persistencia_proveedor.txt",
        "titulo": "E2E: un proveedor creado sigue en el listado tras reiniciar el servidor",
        "entradas": "Navegador Chromium headless contra la app real; proveedor \"Proveedor Persistente E2E\" creado por la UI; el proceso uvicorn se detiene y se vuelve a levantar con la MISMA BD (sin volver a sembrar).",
        "esperado": "Tras el reinicio, el proveedor (con su correo) sigue en el listado junto a los del seed. (REQ-011: los datos persisten al reiniciar)",
        "nodos": [f"{E2E}::test_proveedor_creado_sigue_en_el_listado_tras_reiniciar_el_servidor"],
        "nota": "Cierra la brecha conocida de CP-020 (RUN-006): ahora el proveedor se verifica directamente tras un reinicio real del servidor.",
        "capturas": [f"EV-014_CP-020_{n}.png" for n in ("01_proveedor_antes_de_reiniciar", "02_proveedor_despues_de_reiniciar")],
    },
]


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def pytest_version():
    p = subprocess.run([sys.executable, "-m", "pytest", "--version"], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    return (p.stdout + p.stderr).strip().splitlines()[0]


DIFF_PATHS = ["app", "seeds", "requirements.txt"]


def _cabecera_e2e():
    """Demuestra que la app probada es la del tag: HEAD, qa-build-1 y la salida de git diff (debe ser vacía)."""
    d_head = git("diff", "qa-build-1", "HEAD", "--stat", "--", *DIFF_PATHS)
    d_tree = git("diff", "qa-build-1", "--stat", "--", *DIFF_PATHS)
    return [
        f"HEAD (completo)  : {git('rev-parse', 'HEAD')}",
        f"qa-build-1      : {git('rev-list', '-n', '1', 'qa-build-1')}",
        "Los E2E no existen en el tag qa-build-1: se ejecutan en HEAD. La app es la del tag si la salida de estos comandos está vacía:",
        f"  git diff qa-build-1 HEAD --stat -- app seeds requirements.txt  ->  {d_head or '(salida vacía)'}",
        f"  git diff qa-build-1 --stat -- app seeds requirements.txt (árbol de trabajo)  ->  {d_tree or '(salida vacía)'}",
    ]


SELECCION = set(sys.argv[3:])  # opcional: ids de CP a ejecutar (por defecto, todos), p. ej.: CP-004 CP-005
resumen = []
for caso in CASOS:
    if SELECCION and caso.get("sel", caso["cp"]) not in SELECCION:
        continue
    inicio = datetime.datetime.now().astimezone()
    t0 = time.perf_counter()
    cmd = [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "--no-header", "-W", "ignore", *(["-m", "e2e"] if caso.get("e2e") else []), *caso["nodos"]]
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    duracion = time.perf_counter() - t0
    salida = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]

    sucio = git("status", "--porcelain", "--untracked-files=no")
    descr = git("describe", "--tags", "--exact-match", "HEAD") or "(sin tag exacto)"
    lineas = [
        f"{caso['ev']} - {caso['cp']}: {caso['titulo']}",
        "=" * 78,
        f"Caso de prueba  : {caso['cp']}",
        f"Requisito       : {caso['req']}",
        f"Ejecución       : {caso['run']}",
        f"Fecha/hora      : {inicio.strftime('%Y-%m-%d %H:%M:%S %z')}",
        f"Commit probado  : {git('rev-parse', '--short', 'HEAD')} ({descr})   build de QA: qa-build-1 -> {git('rev-list', '-n', '1', '--abbrev-commit', 'qa-build-1')}",
        f"Árbol de trabajo: {'limpio (sin cambios en archivos versionados)' if not sucio else 'CON CAMBIOS: ' + sucio}",
        *(_cabecera_e2e() if caso.get("e2e") else []),
        f"Entorno         : Python {platform.python_version()} / {platform.system()} {platform.release()} / {pytest_version()} / BD SQLite temporal por prueba",
        "",
        f"ENTRADAS EXACTAS: {caso['entradas']}",
        f"RESULTADO ESPERADO (de las reglas, no del código): {caso['esperado']}",
        *([f"NOTA: {caso['nota']}"] if caso.get("nota") else []),
        "",
        ("Comando: python -m pytest -v " + ("-m e2e " if caso.get("e2e") else "") + " ".join(caso["nodos"])).strip(),
        "",
        *salida,
        "",
        "VERIFICACIONES",
    ]
    checks = []
    checks.append((f"pytest terminó con código {p.returncode} (0 = todas pasan)", p.returncode == 0))
    for nodo in caso["nodos"]:
        ok_pass = any(ln.startswith(nodo) and "PASSED" in ln for ln in salida)
        hay_fallo = any(ln.startswith(nodo) and ("FAILED" in ln or "ERROR" in ln) for ln in salida)
        checks.append((f"{nodo.split('::', 1)[1]}: PASSED en {nodo.split('::', 1)[0]}", ok_pass and not hay_fallo))
    if caso.get("e2e"):
        checks.append(("git diff qa-build-1 HEAD --stat -- app seeds requirements.txt: salida vacía (la app es la del tag)", git("diff", "qa-build-1", "HEAD", "--stat", "--", *DIFF_PATHS) == ""))
        for cap in caso.get("capturas", []):
            checks.append((f"captura guardada: 04_Evidencias/e2e/{cap}", (OUT / "e2e" / cap).is_file()))
    resumen_py = next((ln for ln in reversed(salida) if " passed" in ln or " failed" in ln or " error" in ln), "")
    fallan = re.search(r"(\d+) (failed|error)", resumen_py)
    checks.append((f"resumen real de pytest: {resumen_py.strip('= ')!r} (sin fallos ni errores)", not fallan and "passed" in resumen_py))
    if caso.get("esperado_passed"):  # suite completa: el número de pruebas pasadas debe ser el esperado
        m_pas = re.search(r"(\d+) passed", resumen_py)
        checks.append((f"{caso['esperado_passed']} pruebas pasadas (resultado esperado)", bool(m_pas) and int(m_pas.group(1)) == caso["esperado_passed"]))
    for desc, ok in checks:
        lineas.append(f"  {'OK   ' if ok else 'FALLA'}  {desc}")
    todo = all(ok for _, ok in checks)
    n_pasan = re.search(r"(\d+) passed", resumen_py)
    lineas += ["", f"RESULTADO OBTENIDO: {'PASA' if todo else 'FALLA'}  ({sum(ok for _, ok in checks)}/{len(checks)} verificaciones; {n_pasan.group(1) if n_pasan else '?'} pruebas pasadas)"]
    (OUT / caso["archivo"]).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    resumen.append({
        "run": caso["run"], "ev": caso["ev"], "cp": caso["cp"], "archivo": caso["archivo"], "resultado": "Pasa" if todo else "Falla",
        "inicio": inicio.strftime("%Y-%m-%d %H:%M"), "duracion_s": round(duracion, 1), "pruebas": int(n_pasan.group(1)) if n_pasan else None,
        "pytest": resumen_py.strip("= "), "commit": git("rev-parse", "--short", "HEAD"),
    })
    print(f"{caso['run']} {caso['cp']}: {'PASA' if todo else 'FALLA'} - {resumen_py.strip('= ')}")

RESUMEN.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
sys.exit(0 if all(r["resultado"] == "Pasa" for r in resumen) else 1)
