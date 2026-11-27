# Sistema de Gestión de Licitaciones (ISW-622)

## Descripción
Aplicación web local para gestionar licitaciones de compra: se registran proveedores y licitaciones (Borrador → Publicada → Cerrada), los proveedores presentan ofertas antes del cierre, y el sistema elige la mejor oferta (la más barata), calcula el ahorro frente al presupuesto y determina qué nivel aprueba (Encargado de área, Gerencia o Junta Directiva) según rangos configurables. Los importes se guardan en colones (CRC) y se pueden ver en dólares con el tipo de cambio; hay API REST, interfaz web, inicio de sesión y un ciclo completo de QA (pruebas unitarias, de API y E2E, Postman y rendimiento).
Práctica integradora de ISW-622 (Pruebas de Software, UTN). Equipo: Iván e Ian.
Entrega: viernes 27 de noviembre de 2026.

Reglas de negocio: ver `CLAUDE.md`. Contrato técnico (BD, API, UI): ver `docs/contrato.md`.

## Requisitos
- Windows 10/11, PowerShell, Git for Windows
- Python 3.11+
- Versiones probadas: Python 3.15.2 y pytest 9.2.0 (Iván); Python 3.14.6 (Ian)

## Instalación (Windows PowerShell)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
git config core.hooksPath .githooks
```
El último comando activa el hook `commit-msg` (formato `tipo(módulo): descripción`, sin coautoría de IA).

## Cómo ejecutar
Con el entorno virtual activado y `.env` creado:
```powershell
python -m seeds.seed --reset          # primera vez: crea la BD con los datos de referencia
uvicorn app.main:app --reload         # http://127.0.0.1:8000  (API docs en /docs si ENV != prod)
```
Variables (`.env`): `DATABASE_URL`, `SECRET_KEY`, `ENV`, `EXCHANGE_RATE_URL` (ver `.env.example`).
`EXCHANGE_RATE_URL` es el servicio externo del botón "Sugerir tasa" (default `https://open.er-api.com/v6/latest/USD`, se lee `rates["CRC"]`, timeout 3 s). Con `ENV=test` nunca se consulta; si el servicio falla se usa la última tasa guardada o 500.00.

## Conexión a la base de datos
La aplicación usa **SQLite en un archivo**: no hay servidor de base de datos que instalar. La conexión se define con `DATABASE_URL` en `.env` (se copia de `.env.example`):
```
DATABASE_URL=sqlite:///./licitaciones.db
```
- **Dónde queda:** el archivo `licitaciones.db` se crea al iniciar la app o al correr el seed, **en el directorio desde el que se ejecuta** (la ruta es relativa; si se corre desde la raíz del repositorio, queda en la raíz).
- **No se versiona:** `.env` y `*.db` están en `.gitignore`. Cada máquina tiene su propia BD; lo que se comparte es el código y el seed.
- **Resetearla:** `python -m seeds.seed --reset` (ver la sección siguiente). También sirve borrar `licitaciones.db` y volver a sembrar.
- Para usar otro archivo, cambiar `DATABASE_URL` (por ejemplo `sqlite:///./otra.db`). Las pruebas automáticas usan siempre una BD temporal propia y no tocan `licitaciones.db`.

## Cómo resetear la BD
```powershell
python -m seeds.seed --reset
```
Borra todas las tablas y deja la BD en el estado de referencia (2 usuarios, 3 rangos de aprobación, tasa 500, proveedores P1/P2, licitación LIC-2026-001 con sus 2 ofertas). Sin `--reset` solo siembra si la BD está vacía.

## Usuarios de prueba (sintéticos)
| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin#2026-test` | admin |
| `operador` | `Operador#2026-test` | operador |

## Cómo correr los tests
```powershell
pytest                    # unit + api (los e2e NO corren por defecto: pytest.ini usa -m "not e2e")
pytest tests/unit tests/api
pytest --cov=app
```
Cada prueba usa una BD SQLite temporal limpia, `FakeClock` y un proveedor de tipo de cambio que falla (nunca hay red).

### Pruebas E2E (Playwright)
Las pruebas de extremo a extremo (`tests/e2e/`, marca `e2e`) abren Chromium headless contra la app **real**: la fixture levanta `uvicorn` en un puerto libre con una BD SQLite temporal sembrada con el seed (credenciales `admin` de la tabla de arriba) y `ENV=test`, que usa un proveedor de tipo de cambio falso (sin red). No tocan `licitaciones.db`.
```powershell
python -m playwright install chromium     # una sola vez
pytest tests/e2e -m e2e                   # todas las E2E (CP-011, CP-012, CP-013 y CP-020)
pytest tests/e2e -m e2e -k reiniciar       # una sola, por nombre (aquí: CP-020)
```
Dejan capturas en `04_Evidencias/e2e/` (se sobrescriben en cada corrida). Cada E2E arranca su propio servidor y su BD, así que no dependen unas de otras; la de CP-020 detiene y vuelve a levantar uvicorn con la misma BD.

## Pruebas de API con Postman
Colección con 17 peticiones y 53 aserciones (éxitos y escenarios negativos) en `postman/`. Con la app levantada sobre el seed limpio (`python -m seeds.seed --reset` y `uvicorn app.main:app`):
```powershell
npx newman run postman/licitaciones.postman_collection.json -e postman/local.postman_environment.json
```
Detalle, entorno y qué verifica cada petición: [`postman/README.md`](postman/README.md).

## Prueba de rendimiento
`GET /api/tenders` con 5 usuarios virtuales durante 30 s sobre la app local (criterio REQ-014: p95 ≤ 1 500 ms y errores ≤ 5 %). Con la app levantada sobre el seed:
```powershell
pip install psutil                                   # opcional: mide CPU y RAM del servidor (no está en requirements.txt)
$env:PERF_PASSWORD = "<contraseña de prueba de la tabla de usuarios>"
python scripts/perf/perf_get_listado.py --url http://127.0.0.1:8000
```
Opciones, requisitos y salida: [`scripts/perf/README.md`](scripts/perf/README.md).

## Repositorio
- GitHub: https://github.com/IvanB012/licitaciones-qa-isw622
- Tags:

| Tag | Commit | Qué marca |
|---|---|---|
| `qa-build-1` | `e65b2d8` | Build de QA: el código sobre el que se ejecutan las pruebas |
| `bug-001-defecto` | `8d33f5b` | Commit que introduce el defecto controlado BUG-001 |
| `bug-001-fix` | `5fe825a` | Commit que corrige BUG-001 |

## Mapa de entregables
| Componente del enunciado | En este repositorio | En el paquete de entrega (ZIP) |
|---|---|---|
| `01_Software/` | La raíz del repositorio: `app/`, `seeds/`, `tests/`, `scripts/`, `postman/`, `docs/`, `requirements.txt`, `.env.example` y `pytest.ini` | La carpeta `01_Software/` |
| `README.md` | Raíz del repositorio | Raíz del ZIP |
| `02_Plan_Informe_QA.docx` y `02_Plan_Informe_QA.pdf` | Raíz del repositorio | Raíz del ZIP |
| `03_Registro_QA.xlsx` | Raíz del repositorio | Raíz del ZIP |
| `04_Evidencias/` | Carpeta `04_Evidencias/`, con [`INDICE.md`](04_Evidencias/INDICE.md) | Carpeta `04_Evidencias/` |
| `05_IA/` | Carpeta `05_IA/` (un `IA-###.md` por intervención) | Carpeta `05_IA/` |

El paquete de entrega se genera con `git archive` del código más los documentos finales; no incluye `.venv`, `.env` ni bases de datos.

## Estructura de carpetas
```
app/        config.py db.py models.py clock.py exchange.py errors.py deps.py main.py
            rules/ services/ api/ web/ (plantillas en web/templates) static/ (vendor/bootstrap local)
tests/      unit/ api/ e2e/   (conftest.py con las fixtures; e2e/ = pruebas Playwright con su propio conftest.py)
seeds/      seed.py
scripts/    ejecutar_cp.py (ejecuta CP y genera evidencias), ejecutar_postman.py, ejecutar_seguridad.py, perf/ (prueba de rendimiento)
docs/       contrato.md, casos_prueba.md (20 CP), trazabilidad.md (REQ ↔ CP ↔ tests), automatizacion.md (pruebas automatizadas)
postman/    colección de la API
04_Evidencias/  salidas reales, capturas, logs (EV-###)
05_IA/          declaración de uso de IA (IA-###.md)
.claude/    configuración, skills y comandos de Claude Code
.githooks/  commit-msg
```

## Uso de IA
La IA se declara en `05_IA/` (un archivo `IA-###.md` por intervención) y en el Excel de QA, **no** en git.
