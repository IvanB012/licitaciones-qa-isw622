# Sistema de Gestión de Licitaciones (ISW-622)

## Descripción
<!-- Completar: app web local para gestionar licitaciones, proveedores y ofertas, con ciclo completo de QA. -->
Práctica integradora de ISW-622 (Pruebas de Software, UTN). Equipo: Iván e Ian.
Entrega: viernes 27 de noviembre de 2026.

Reglas de negocio: ver `CLAUDE.md`. Contrato técnico (BD, API, UI): ver `docs/contrato.md`.

## Requisitos
- Windows 10/11, PowerShell, Git for Windows
- Python 3.11+
<!-- Completar versiones probadas -->

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
Variables (`.env`): `DATABASE_URL`, `SECRET_KEY`, `ENV` (ver `.env.example`).

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
pytest                    # unit + api (e2e cuando existan)
pytest tests/unit tests/api
pytest tests/e2e          # requiere chromium (playwright install chromium)
pytest --cov=app
```
Cada prueba usa una BD SQLite temporal limpia, `FakeClock` y un proveedor de tipo de cambio que falla (nunca hay red).

## Estructura de carpetas
```
app/        config.py db.py models.py clock.py exchange.py errors.py deps.py main.py
            rules/ services/ api/ web/ (plantillas en web/templates) static/ (vendor/bootstrap local)
tests/      unit/ api/ e2e/   (conftest.py con las fixtures)
seeds/      seed.py
docs/       contrato.md
postman/    colección de la API
04_Evidencias/  salidas reales, capturas, logs (EV-###)
05_IA/          declaración de uso de IA (IA-###.md)
.claude/    configuración, skills y comandos de Claude Code
.githooks/  commit-msg
```

## Uso de IA
La IA se declara en `05_IA/` (un archivo `IA-###.md` por intervención) y en el Excel de QA, **no** en git.
