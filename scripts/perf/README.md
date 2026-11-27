# Prueba de rendimiento — CP-018 (REQ-014)

`perf_get_listado.py` mide el tiempo de respuesta de `GET /api/tenders` con **5 usuarios virtuales durante 30 s** sobre la aplicación **local**, con datos sintéticos.

**Criterio (REQ-014):** p95 ≤ 1 500 ms y tasa de error ≤ 5 %.

> **Autorización de la práctica:** solo la aplicación del equipo, en `localhost`, con un tope **duro** de 5 usuarios y 30 s (si se piden más, el script los recorta; si la URL no es local, se niega a correr).

## Requisitos

- Python 3.11+ con `httpx` (ya está en `requirements.txt`).
- **Opcional:** `psutil`, para medir CPU y RAM del proceso de uvicorn. **No** está en `requirements.txt`; se instala aparte:
  ```powershell
  pip install psutil
  ```
  Sin `psutil`, el script avisa y solo omite esa medición.

## Cómo ejecutarla

```powershell
# 1. BD con el seed de referencia (datos sintéticos) y la app en una sola terminal
python -m seeds.seed --reset
python -m uvicorn app.main:app --port 8000

# 2. En otra terminal: la contraseña NO está en el código; se lee del entorno
$env:PERF_PASSWORD = "<contraseña de prueba del README>"     # usuario por defecto: operador (PERF_USER)
python scripts/perf/perf_get_listado.py --url http://127.0.0.1:8000
```

Opciones útiles: `--ev EV-069 --run RUN-061` (además escribe `04_Evidencias/EV-069_CP-018_rendimiento_informe.txt` con el encabezado de evidencia) y `--app-repo <ruta>` (repositorio o *worktree* desde el que corre la app, para anotar su commit y tag). Para medir el build de QA congelado:

```powershell
git worktree add --detach ..\_tag_qa_build_1 qa-build-1
# levantar uvicorn desde esa carpeta y pasar --app-repo ..\_tag_qa_build_1
```

Cierre programas pesados antes de medir y no use la máquina durante los 30 s.

## Qué genera (en `04_Evidencias/perf/`)

| Archivo | Contenido |
|---|---|
| `perf_<fecha>_peticiones.csv` | Una fila por petición: usuario virtual, instante relativo, estado HTTP, tiempo (ms) y error |
| `perf_<fecha>_recursos.csv` | CPU y RAM del proceso del servidor y CPU total de la máquina, una muestra por segundo |
| `perf_<fecha>_resumen.json` | Metadatos (commit, máquina, versiones) y métricas: total, throughput, media, p50, p95, p99, errores |

Al final imprime **Cumple** o **No cumple** frente al umbral, con los valores reales. El percentil se calcula por rango más cercano (*nearest-rank*).

## Notas para interpretar los resultados

- La **CPU del servidor** se expresa como porcentaje de **un núcleo**, por lo que puede superar el 100 % (uvicorn atiende los endpoints síncronos con un grupo de hilos).
- El cliente de carga corre **en la misma máquina** que el servidor y le quita CPU: el resultado es conservador.
- El inicio de sesión de cada usuario se hace **antes** de empezar a medir y no cuenta en los tiempos.
- Si no cumple el umbral, hay que registrar el resultado real y conservar **todas** las corridas.
