# Rendimiento — Ian (hoja `15_Rendimiento`)

> Borrador con las columnas de la hoja 15. **El Excel oficial lo llena solo Iván**, copiando de aquí.
> Solo se registra lo realmente ejecutado. Si no cumple el umbral se registra el resultado real; si se repite, se conservan todas las corridas.

| PERF ID | REQ | Herramienta (nombre y versión) | Tipo | Usuarios | Duración (s) | p95 (ms) | Tasa de error (%) | Throughput (req/s) | CPU (%) | RAM (MB) | Umbral esperado | Resultado | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PERF-001 | REQ-014 · CP-018 · RUN-061 | Script propio `scripts/perf/perf_get_listado.py` (Python 3.14.6, httpx 0.29.0, psutil 7.2.2) | Carga local: `GET /api/tenders` (listado) | 5 | 30 (real: 30,02) | 54,59 | 0,0 (0 errores de 4 024 peticiones) | 134,05 | Servidor: prom 124,2 · mín 99,3 · máx 139,5 (% de un núcleo). Máquina completa: prom 61,3 · máx 91,6 | Servidor: prom 97,5 · mín 97,3 · máx 97,5 | p95 ≤ 1 500 ms y tasa de error ≤ 5 % | **Cumple** | EV-069 y `04_Evidencias/perf/perf_20261126_224750_*` (peticiones.csv, recursos.csv, resumen.json) |

## Métricas completas (de EV-069)

| Métrica | Valor |
|---|---|
| Peticiones totales | 4 024 (todas HTTP 200) |
| Tiempo de respuesta | media 37,27 ms · mín 18,22 · p50 35,4 · p95 54,59 · p99 66,5 · máx 92,63 |
| Peticiones por usuario virtual | 809 · 810 · 804 · 799 · 802 |
| Muestras de CPU/RAM | 29 (una por segundo) |

## Configuración de la máquina y del entorno

| Elemento | Valor |
|---|---|
| CPU | 13th Gen Intel(R) Core(TM) i7-1355U (12 CPU lógicas) |
| RAM | 15,6 GB |
| Sistema operativo | Windows 11 (10.0.26200) |
| Aplicación | commit `e65b2d8` = `qa-build-1`, ejecutada desde un *worktree* del tag, árbol limpio; un solo proceso de uvicorn (pid 37160), sin `--reload` |
| Base de datos | SQLite temporal con el seed de referencia (1 licitación, 2 proveedores, 2 ofertas) |
| Cliente de carga | 5 hilos con `httpx`, una sesión por usuario (inicio de sesión previo a la medición) |

## Notas

- **Verificación independiente:** el p95 se recalculó desde el CSV con un método distinto (interpolado) y dio 54,59 ms, igual que el del script (rango más cercano).
- **Una sola corrida:** no se repitió. Quedó una corrida de humo de 3 s previa (p95 44,27 ms) que sirvió solo para comprobar el script y **no** se guardó como evidencia.
- **Limitaciones:** el seed tiene una sola licitación, así que el listado es pequeño; el cliente de carga corre en la misma máquina que el servidor (le quita CPU, el resultado es conservador); había otro `uvicorn` inactivo en el puerto 8000; la máquina no estaba aislada (otros programas abiertos).
- **CPU del servidor:** se expresa como porcentaje de **un núcleo**, por lo que supera el 100 % (uvicorn atiende los endpoints síncronos con un grupo de hilos).
- **Autorización/alcance:** solo la aplicación del equipo, en `localhost`, con datos sintéticos y con el tope de la práctica de 5 usuarios y 30 s (el script lo impone).
