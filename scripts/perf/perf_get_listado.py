"""Prueba de carga LOCAL de GET /api/tenders (CP-018, REQ-014).

5 usuarios virtuales (hilos) durante 30 s contra la aplicación local, con datos sintéticos.
Criterio (REQ-014): p95 <= 1500 ms y tasa de error <= 5 %.

Autorización de la práctica: solo la aplicación del equipo, en localhost, con tope DURO de 5 usuarios y 30 s
(si se piden más, se recortan a ese tope).

Las credenciales NO están en el código: se leen de las variables de entorno PERF_USER (por defecto "operador")
y PERF_PASSWORD (obligatoria; usar la contraseña de prueba del README).

CPU y RAM del proceso de uvicorn se miden con psutil (opcional: ``pip install psutil``; no está en requirements.txt).
Sin psutil, el script avisa y omite esa medición.

Uso (ver scripts/perf/README.md):
    python scripts/perf/perf_get_listado.py [--url http://127.0.0.1:8000] [--ev EV-069 --run RUN-061 --app-repo <ruta>]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

try:
    import psutil
except ImportError:  # opcional
    psutil = None

MAX_USERS = 5
MAX_SECONDS = 30
THRESHOLD_P95_MS = 1500.0
THRESHOLD_ERROR_PCT = 5.0

REPO = Path(__file__).resolve().parents[2]


def percentile(sorted_values: list[float], pct: float) -> float:
    """Percentil por el método del rango más cercano (nearest-rank)."""
    if not sorted_values:
        return float("nan")
    rank = max(1, math.ceil(pct / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    except OSError:
        return ""


def machine_info() -> dict:
    cpu_name = platform.processor() or "desconocido"
    if sys.platform == "win32":
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                capture_output=True, text=True, encoding="utf-8", timeout=20,
            ).stdout.strip()
            if out:
                cpu_name = out.splitlines()[0].strip()
        except (OSError, subprocess.SubprocessError):
            pass
    ram_gb = round(psutil.virtual_memory().total / 2**30, 1) if psutil else None
    return {
        "cpu": cpu_name,
        "cpus_logicas": os.cpu_count(),
        "ram_total_gb": ram_gb,
        "so": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python": platform.python_version(),
        "httpx": httpx.__version__,
        "psutil": psutil.__version__ if psutil else None,
    }


def find_server_process(port: int):
    """Proceso que escucha en el puerto (el de uvicorn). Devuelve None si no se puede identificar."""
    if not psutil:
        return None
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == port and conn.pid:
                return psutil.Process(conn.pid)
    except (psutil.Error, OSError):
        pass
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmd = " ".join(proc.info.get("cmdline") or [])
        if "uvicorn" in cmd and str(port) in cmd:
            return proc
    return None


class ResourceSampler(threading.Thread):
    """Muestrea cada segundo la CPU y la RAM del proceso del servidor y la CPU total de la máquina."""

    def __init__(self, proc):
        super().__init__(daemon=True)
        self.proc = proc
        self.stop = threading.Event()
        self.samples: list[tuple[float, float, float, float]] = []  # (t_s, cpu_proc_%, rss_mb, cpu_sistema_%)

    def run(self):
        t0 = time.perf_counter()
        self.proc.cpu_percent(None)  # primera llamada: inicializa el contador
        psutil.cpu_percent(None)
        while not self.stop.wait(1.0):
            try:
                self.samples.append((
                    round(time.perf_counter() - t0, 1),
                    self.proc.cpu_percent(None),
                    round(self.proc.memory_info().rss / 2**20, 1),
                    psutil.cpu_percent(None),
                ))
            except psutil.Error:
                break


def main() -> int:
    ap = argparse.ArgumentParser(description="Prueba de carga local de GET /api/tenders (REQ-014).")
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--path", default="/api/tenders")
    ap.add_argument("--users", type=int, default=MAX_USERS)
    ap.add_argument("--seconds", type=int, default=MAX_SECONDS)
    ap.add_argument("--out", default=str(REPO / "04_Evidencias" / "perf"), help="carpeta de CSV/JSON")
    ap.add_argument("--app-repo", default=str(REPO), help="repositorio/worktree desde el que corre la app (para anotar el commit)")
    ap.add_argument("--ev", help="id de evidencia (p. ej. EV-069): además escribe 04_Evidencias/<EV>_CP-018_rendimiento.txt")
    ap.add_argument("--run", default="", help="id de ejecución (p. ej. RUN-061) para el encabezado")
    args = ap.parse_args()

    users, seconds = min(args.users, MAX_USERS), min(args.seconds, MAX_SECONDS)
    if (users, seconds) != (args.users, args.seconds):
        print(f"AVISO: la autorización de la práctica limita la carga a {MAX_USERS} usuarios y {MAX_SECONDS} s; se recorta a {users} usuarios y {seconds} s.")
    username, password = os.environ.get("PERF_USER", "operador"), os.environ.get("PERF_PASSWORD")
    if not password:
        print("ERROR: defina PERF_PASSWORD (contraseña de prueba del README) en el entorno.", file=sys.stderr)
        return 2
    host = urlparse(args.url).hostname or ""
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("ERROR: solo se permite probar la aplicación local (localhost).", file=sys.stderr)
        return 2
    port = urlparse(args.url).port or 80

    try:
        httpx.get(args.url + "/api/health", timeout=5).raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ERROR: la aplicación no responde en {args.url} ({type(exc).__name__}).", file=sys.stderr)
        return 2

    proc = find_server_process(port)
    sampler = ResourceSampler(proc) if proc else None
    if not psutil:
        print("AVISO: psutil no está instalado; se omite la medición de CPU/RAM (pip install psutil).")
    elif not proc:
        print("AVISO: no se pudo identificar el proceso del servidor; se omite la medición de CPU/RAM.")

    results: list[tuple[int, float, int, float, int]] = []  # (vu, t_rel_s, status, ms, error)
    lock = threading.Lock()
    login_ok = [False] * users
    shared = {"start": 0.0, "deadline": 0.0}

    def arrancar():  # se ejecuta una sola vez, cuando los usuarios ya iniciaron sesión
        shared["start"] = time.perf_counter()
        shared["deadline"] = shared["start"] + seconds
        if sampler:
            sampler.start()

    barrier = threading.Barrier(users, action=arrancar, timeout=60)

    def vu(idx: int):
        local: list[tuple[int, float, int, float, int]] = []
        with httpx.Client(base_url=args.url, timeout=10) as client:
            try:
                r = client.post("/api/auth/login", json={"username": username, "password": password})
                login_ok[idx] = r.status_code == 200
            except httpx.HTTPError:
                login_ok[idx] = False
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                return
            if not login_ok[idx]:
                return
            while time.perf_counter() < shared["deadline"]:
                t0 = time.perf_counter()
                try:
                    status = client.get(args.path).status_code
                    error = int(status >= 400)
                except httpx.HTTPError:
                    status, error = 0, 1
                ms = (time.perf_counter() - t0) * 1000
                local.append((idx + 1, round(t0 - shared["start"], 3), status, round(ms, 2), error))
        with lock:
            results.extend(local)

    inicio = datetime.datetime.now().astimezone()
    hilos = [threading.Thread(target=vu, args=(i,)) for i in range(users)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    wall = time.perf_counter() - shared["start"] if shared["start"] else 0.0
    if sampler:
        sampler.stop.set()
        sampler.join(timeout=3)

    if not all(login_ok) or not results:
        print(f"ERROR: la prueba no es válida (inicios de sesión correctos: {sum(login_ok)}/{users}; peticiones: {len(results)}).", file=sys.stderr)
        return 3

    ms = sorted(r[3] for r in results)
    total, errores = len(results), sum(r[4] for r in results)
    metrics = {
        "peticiones": total,
        "errores": errores,
        "tasa_error_pct": round(errores / total * 100, 3),
        "throughput_rps": round(total / wall, 2) if wall else None,
        "duracion_real_s": round(wall, 2),
        "media_ms": round(statistics.fmean(ms), 2),
        "min_ms": round(ms[0], 2), "p50_ms": round(percentile(ms, 50), 2), "p95_ms": round(percentile(ms, 95), 2),
        "p99_ms": round(percentile(ms, 99), 2), "max_ms": round(ms[-1], 2),
    }
    if sampler and sampler.samples:
        cpu_p = [s[1] for s in sampler.samples]
        rss = [s[2] for s in sampler.samples]
        cpu_s = [s[3] for s in sampler.samples]
        metrics.update({
            "muestras_recursos": len(sampler.samples),
            "cpu_proceso_pct": {"min": min(cpu_p), "prom": round(statistics.fmean(cpu_p), 1), "max": max(cpu_p)},
            "ram_proceso_mb": {"min": min(rss), "prom": round(statistics.fmean(rss), 1), "max": max(rss)},
            "cpu_sistema_pct": {"min": min(cpu_s), "prom": round(statistics.fmean(cpu_s), 1), "max": max(cpu_s)},
        })
    cumple_p95 = metrics["p95_ms"] <= THRESHOLD_P95_MS
    cumple_err = metrics["tasa_error_pct"] <= THRESHOLD_ERROR_PCT
    veredicto = "Cumple" if cumple_p95 and cumple_err else "No cumple"

    stamp = inicio.strftime("%Y%m%d_%H%M%S")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    csv_path, json_path = out / f"perf_{stamp}_peticiones.csv", out / f"perf_{stamp}_resumen.json"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vu", "t_relativo_s", "http_status", "tiempo_ms", "error"])
        w.writerows(sorted(results, key=lambda r: r[1]))
    recursos_path = None
    if sampler and sampler.samples:
        recursos_path = out / f"perf_{stamp}_recursos.csv"
        with recursos_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t_s", "cpu_proceso_pct", "ram_proceso_mb", "cpu_sistema_pct"])
            w.writerows(sampler.samples)

    app_repo = Path(args.app_repo)
    maquina = machine_info()
    meta = {
        "fecha": inicio.strftime("%Y-%m-%d %H:%M:%S %z"),
        "url": args.url, "ruta": args.path, "usuarios": users, "duracion_pedida_s": seconds,
        "commit_app": git(app_repo, "rev-parse", "--short", "HEAD"),
        "tag_app": git(app_repo, "describe", "--tags", "--exact-match", "HEAD") or "sin tag",
        "commit_script": git(REPO, "rev-parse", "--short", "HEAD"),
        "proceso_servidor": {"pid": proc.pid, "nombre": proc.name()} if proc else None,
        "maquina": maquina,
    }
    json_path.write_text(json.dumps({"meta": meta, "metricas": metrics, "umbral": {"p95_ms": THRESHOLD_P95_MS, "error_pct": THRESHOLD_ERROR_PCT}, "veredicto": veredicto},
                                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def rng(d):
        return f"mín {d['min']} · prom {d['prom']} · máx {d['max']}"

    ev = args.ev
    lineas = []
    if ev:
        lineas += [
            f"{ev} - CP-018: Rendimiento del listado, {users} usuarios virtuales durante {seconds} s", "=" * 78,
            "Caso de prueba  : CP-018", "Requisito       : REQ-014", f"Ejecución       : {args.run or '(sin RUN)'}",
            f"Fecha/hora      : {meta['fecha']}",
            f"Aplicación      : commit {meta['commit_app']} ({meta['tag_app']}) = build de QA qa-build-1; {args.url}; BD SQLite con el seed de referencia (datos sintéticos)",
            f"Script          : scripts/perf/perf_get_listado.py (commit {meta['commit_script']})",
            f"Entorno         : Python {maquina['python']} / httpx {maquina['httpx']} / psutil {maquina['psutil']}",
            f"Máquina         : {maquina['cpu']} ({maquina['cpus_logicas']} CPU lógicas), {maquina['ram_total_gb']} GB de RAM, {maquina['so']}",
            "Usuario         : operador (credenciales de prueba del README; no se reproducen aquí)", "",
            f"OBJETIVO: GET {args.path} con {users} usuarios virtuales concurrentes durante {seconds} s sobre la aplicación local.",
            f"RESULTADO ESPERADO (de las reglas, no del código): p95 <= {THRESHOLD_P95_MS:.0f} ms y tasa de error <= {THRESHOLD_ERROR_PCT:.0f} %. (REQ-014)", "",
        ]
    lineas += [
        "RESULTADOS",
        f"  Peticiones totales : {metrics['peticiones']}  (errores: {metrics['errores']})",
        f"  Duración real      : {metrics['duracion_real_s']} s     Throughput: {metrics['throughput_rps']} req/s",
        f"  Tiempo de respuesta: media {metrics['media_ms']} ms · mín {metrics['min_ms']} · p50 {metrics['p50_ms']} · p95 {metrics['p95_ms']} · p99 {metrics['p99_ms']} · máx {metrics['max_ms']} ms",
        f"  Tasa de error      : {metrics['tasa_error_pct']} %",
    ]
    if "cpu_proceso_pct" in metrics:
        lineas += [
            f"  CPU del servidor   : {rng(metrics['cpu_proceso_pct'])} %  (de un núcleo; proceso pid {proc.pid})",
            f"  RAM del servidor   : {rng(metrics['ram_proceso_mb'])} MB",
            f"  CPU total máquina  : {rng(metrics['cpu_sistema_pct'])} %   ({metrics['muestras_recursos']} muestras, 1 por segundo)",
        ]
    else:
        lineas.append("  CPU/RAM            : no medidas (sin psutil o sin proceso identificado)")
    lineas += [
        "", "VERIFICACIONES",
        f"  {'OK   ' if all(login_ok) else 'FALLA'}  los {users} usuarios iniciaron sesión antes de empezar la carga",
        f"  {'OK   ' if cumple_p95 else 'FALLA'}  p95 = {metrics['p95_ms']} ms (umbral <= {THRESHOLD_P95_MS:.0f} ms)",
        f"  {'OK   ' if cumple_err else 'FALLA'}  tasa de error = {metrics['tasa_error_pct']} % (umbral <= {THRESHOLD_ERROR_PCT:.0f} %)",
        "", f"RESULTADO OBTENIDO: {veredicto.upper()}  (p95 {metrics['p95_ms']} ms; error {metrics['tasa_error_pct']} %)",
        "", "Archivos generados: " + ", ".join([csv_path.name, json_path.name] + ([recursos_path.name] if recursos_path else [])) + f" (en {out.name}/)",
    ]
    texto = "\n".join(lineas)
    print(texto)
    if ev:
        (Path(args.out).parent / f"{ev}_CP-018_rendimiento_informe.txt").write_text(texto + "\n", encoding="utf-8")
    return 0 if veredicto == "Cumple" else 1


if __name__ == "__main__":
    sys.exit(main())
