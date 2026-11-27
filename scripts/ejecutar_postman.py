"""Ejecuta la colección de Postman con newman y guarda la evidencia. El veredicto sale del resultado real de newman.

Uso: python run_newman_ev.py <repo> <app_url> <app_repo_tag> <ev_id> <archivo_salida> "<titulo>" "<objetivo>"
"""
import datetime
import hashlib
import platform
import re
import subprocess
import sys
from pathlib import Path

REPO, URL, APP_REPO, EV, ARCHIVO, TITULO, OBJETIVO = (sys.argv[1], sys.argv[2], sys.argv[3], *sys.argv[4:8])
REPO, APP_REPO = Path(REPO), Path(APP_REPO)
COL = REPO / "postman" / "licitaciones.postman_collection.json"
ENV = REPO / "postman" / "local.postman_environment.json"


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", shell=(sys.platform == "win32"))


def git(repo, *a):
    return run(["git", *a], repo).stdout.strip()


newman_v = run(["npx", "--yes", "newman", "--version"], REPO).stdout.strip().splitlines()[-1]
node_v = run(["node", "--version"], REPO).stdout.strip()
sha = hashlib.sha256(COL.read_bytes()).hexdigest()
inicio = datetime.datetime.now().astimezone()

p = run(["npx", "--yes", "newman", "run", str(COL), "-e", str(ENV), "--env-var", f"base_url={URL}", "--color", "off"], REPO)
salida = [ln.rstrip() for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]


def celda(nombre):
    m = re.search(rf"│\s*{nombre}\s*│\s*(\d+)\s*│\s*(\d+)\s*│", "\n".join(salida))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


reqs, reqs_f = celda("requests")
asers, asers_f = celda("assertions")
checks = [
    (f"newman terminó con código {p.returncode} (0 = sin fallos)", p.returncode == 0),
    (f"requests ejecutadas: {reqs} (esperadas: 17)", reqs == 17),
    (f"requests fallidas: {reqs_f} (esperadas: 0)", reqs_f == 0),
    (f"aserciones ejecutadas: {asers}, fallidas: {asers_f} (esperadas: 0 fallidas)", asers is not None and asers_f == 0),
]
lineas = [
    f"{EV} - {TITULO}",
    "=" * 78,
    "Herramienta     : Postman (colección v2.1) ejecutada con newman por línea de comandos",
    f"Fecha/hora      : {inicio.strftime('%Y-%m-%d %H:%M:%S %z')}",
    f"Aplicación      : commit {git(APP_REPO, 'rev-parse', '--short', 'HEAD')} ({git(APP_REPO, 'describe', '--tags', '--exact-match', 'HEAD') or 'sin tag'}) = build de QA qa-build-1; ejecutada desde un worktree del tag, {URL}",
    f"                  árbol de la app: {'limpio' if not git(APP_REPO, 'status', '--porcelain', '--untracked-files=no') else 'CON CAMBIOS'}; BD SQLite temporal con el seed de referencia",
    f"Colección       : postman/licitaciones.postman_collection.json (SHA-256 {sha[:16]}…) — rama {git(REPO, 'branch', '--show-current')}, base {git(REPO, 'rev-parse', '--short', 'HEAD')}",
    f"Entorno         : newman {newman_v}, Node {node_v}, Windows {platform.release()}; app con Python {platform.python_version()}",
    "Usuario         : operador (credenciales de prueba del README; no se reproducen aquí)",
    "",
    f"OBJETIVO: {OBJETIVO}",
    "RESULTADO ESPERADO (de las reglas, no del código): las 17 peticiones se cumplen con el código HTTP y el cuerpo de los REQ-001, 002, 003, 005, 006, 007, 008, 009, 011 y 012; "
    "los errores tienen exactamente {error, detalle}.",
    "",
    "$ npx newman run postman/licitaciones.postman_collection.json -e postman/local.postman_environment.json --env-var base_url=" + URL,
    "",
    *salida,
    "",
    "VERIFICACIONES",
    *[f"  {'OK   ' if ok else 'FALLA'}  {d}" for d, ok in checks],
    "",
    f"RESULTADO OBTENIDO: {'PASA' if all(ok for _, ok in checks) else 'FALLA'}  ({sum(ok for _, ok in checks)}/{len(checks)} verificaciones)",
]
(REPO / "04_Evidencias" / ARCHIVO).write_text("\n".join(lineas) + "\n", encoding="utf-8")
print(f"{EV}: {'PASA' if all(ok for _, ok in checks) else 'FALLA'} — {reqs} requests, {asers} aserciones, {asers_f} fallidas")
sys.exit(0 if all(ok for _, ok in checks) else 1)
