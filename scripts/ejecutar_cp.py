"""Ejecuta CP automáticos con pytest sobre el commit actual y escribe la evidencia en 04_Evidencias/.

Uso:  python run_cp.py <repo> <salida_json>
Los veredictos salen de la salida real de pytest: código de retorno, cada test pedido en PASSED y ninguno en FAILED.
"""
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
]


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def pytest_version():
    p = subprocess.run([sys.executable, "-m", "pytest", "--version"], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    return (p.stdout + p.stderr).strip().splitlines()[0]


resumen = []
for caso in CASOS:
    inicio = datetime.datetime.now().astimezone()
    t0 = time.perf_counter()
    cmd = [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "--no-header", "-W", "ignore", *caso["nodos"]]
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
        f"Entorno         : Python {platform.python_version()} / {platform.system()} {platform.release()} / {pytest_version()} / BD SQLite temporal por prueba",
        "",
        f"ENTRADAS EXACTAS: {caso['entradas']}",
        f"RESULTADO ESPERADO (de las reglas, no del código): {caso['esperado']}",
        *([f"NOTA: {caso['nota']}"] if caso.get("nota") else []),
        "",
        "Comando: python -m pytest -v " + " ".join(caso["nodos"]),
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
    resumen_py = next((ln for ln in reversed(salida) if " passed" in ln or " failed" in ln or " error" in ln), "")
    fallan = re.search(r"(\d+) (failed|error)", resumen_py)
    checks.append((f"resumen real de pytest: {resumen_py.strip('= ')!r} (sin fallos ni errores)", not fallan and "passed" in resumen_py))
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
