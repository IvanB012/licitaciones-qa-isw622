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
<!-- Completar cuando exista app/main.py -->
```powershell
uvicorn app.main:app --reload
```

## Cómo resetear la BD
<!-- Completar -->
```powershell
python -m seeds.seed --reset
```

## Usuarios de prueba (sintéticos)
<!-- Completar con los usuarios del seed (ver docs/contrato.md §8) -->

## Cómo correr los tests
```powershell
pytest tests/unit tests/api
pytest tests/e2e          # requiere la app y chromium
pytest --cov=app
```

## Estructura de carpetas
```
app/        rules/ services/ api/ web/ static/ templates/
tests/      unit/ api/ e2e/
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
