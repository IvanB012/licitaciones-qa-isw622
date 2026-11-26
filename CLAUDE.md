# CLAUDE.md — Sistema de Gestión de Licitaciones (ISW-622)

## Contexto
Práctica integradora de ISW-622 (UTN). Equipo de 2 (Iván e Ian). Se construye con apoyo de IA una app web local pequeña y se hace un ciclo completo de QA con plantillas Word/Excel del profesor. **Entrega: viernes 27-nov-2026; código y pruebas terminan el jueves 26.** Trabajo rápido: nada de sobreingeniería.

Una licitación es un proceso de compra: una entidad publica una necesidad con presupuesto y fecha/hora de cierre; los proveedores ofertan; tras el cierre no se aceptan ofertas; gana la oferta válida más barata; se calcula el ahorro vs. presupuesto; según el monto ganador aprueba un nivel (Encargado de área, Gerencia, Junta Directiva).

Documento de detalle: `docs/contrato.md` (BD, API, UI, errores). Si algo no está claro, decidir lo más razonable y anotarlo en "Decisiones tomadas" abajo.

## Stack
Python 3.11+, FastAPI, SQLAlchemy, SQLite, Jinja2 (UI en servidor, JS mínimo), Bootstrap 5 **vendorizado** en `app/static/vendor` (sin CDN), pytest, pytest-playwright (E2E), colección Postman en `postman/`. Windows (PowerShell + Git for Windows).

## REGLAS DE NEGOCIO (fuente de verdad = oráculo de las pruebas; jamás inventar reglas)
- **REQ-001 Proveedores**: crear/editar/listar. Nombres equivalentes (recortar espacios, compactar espacios internos, sin distinguir mayúsculas) se rechazan como duplicados.
- **REQ-002 Licitaciones**: código único sin distinguir mayúsculas ni espacios laterales; título no vacío; presupuesto CRC > 0; fecha/hora de cierre futura al crear/publicar.
- **REQ-003 Estados**: solo Borrador→Publicada, Borrador→Cerrada, Publicada→Cerrada. No volver de Publicada a Borrador ni reabrir una Cerrada.
- **REQ-004 Vencimiento**: solo se aceptan ofertas en licitaciones Publicadas y antes del instante de cierre; EXACTAMENTE en el cierre se rechaza (`now >= cierre` rechaza).
- **REQ-005 Montos**: oferta > 0 y <= presupuesto CRC. Igual al presupuesto es válida; cero, negativo o superior se rechazan (un céntimo por encima se rechaza).
- **REQ-006 Duplicados**: un proveedor solo una oferta por licitación; también debe rechazarlo la BD (UNIQUE).
- **REQ-007 Mejor oferta**: gana la menor oferta válida en CRC; en empate gana la registrada primero; sin ofertas se muestra "Sin ofertas válidas".
- **REQ-008 Ahorro** = ((presupuesto − mejor oferta) / presupuesto) × 100. >= 10 %: "Conveniente"; > 0 y < 10 %: "Aceptable"; 0 %: "Válida sin ahorro".
- **REQ-009 Aprobación** por rangos CONFIGURABLES (tabla en BD, sin traslape, validado): 0,01–999 999,99 = Encargado de área; 1 000 000–9 999 999,99 = Gerencia; >= 10 000 000 = Junta Directiva. Nivel según el monto de la mejor oferta válida. Frontera: intervalos semiabiertos [min, max) en céntimos, sin huecos (ver contrato §6).
- **REQ-010 Moneda**: solo se persisten importes en CRC; USD = CRC / (CRC por USD) con tasa > 0; mostrar tasa y fecha usadas; alternar vista CRC/USD NO modifica la BD.
- **REQ-011 Persistencia/API**: los datos persisten al reiniciar; la API devuelve respuestas verificables (éxito y error) y NO acepta valores que la UI no aceptaría (mismas validaciones en ambas).
- **REQ-012 Seguridad**: en nombre de proveedor rechazar caracteres que no sean letras (con tildes y ñ), números, espacios, punto, coma y paréntesis; evitar ejecución de HTML/script (escape en plantillas); ocultar errores internos (sin trazas, rutas ni credenciales).
- **REQ-013 Usabilidad**: con dos personas ajenas, al menos 3 de 4 tareas (registrar proveedor y ofertar) se completan sin ayuda.
- **REQ-014 Rendimiento**: 5 usuarios virtuales, 30 s, GET de listado en local: p95 <= 1500 ms y error <= 5 %.

Extra del enunciado: CRUD completo de TODAS las tablas; autenticación usuario/contraseña (sesión por cookie, contraseñas con hash, usuarios sintéticos en el seed); servicio externo de tipo de cambio.

### Datos semilla de referencia (seed reproducible y reseteable)
- P1 "Tecnología Norte S.A."; P2 "Servicios del Valle".
- L1: LIC-2026-001, presupuesto CRC 10 000 000,00, cierre = ahora + 48 h, Publicada.
- Ofertas L1: P1 = 9 000 000,00; P2 = 9 500 000,00 → gana P1, ahorro 10 % (Conveniente), aprueba Gerencia.
- Tipo de cambio CRC 500,00 por USD (fecha actual) → P1 = USD 18 000,00.
- Escenario aislado: presupuesto 1 000 000,00 con ofertas 900 000 / 950 000 / 1 000 000 (ahorros 10 %, 5 %, 0 %).

## Decisiones técnicas obligatorias
- **Capas**: `app/rules/` (funciones puras, sin BD ni red: normalización, validación de montos, ahorro, aprobador, transiciones) → `app/services/` (casos de uso + BD) → `app/api/` (routers FastAPI) → `app/web/` (plantillas Jinja2, rutas de UI). UI y API usan **LAS MISMAS validaciones** (los services). Ninguna regla se duplica en routers ni plantillas.
- **Dinero**: nunca `float`. CRC persistido como enteros en céntimos; operar con `Decimal`; la API intercambia strings decimales (`"9000000.00"`).
- **Reloj inyectable**: interfaz `Clock` (`now()`); en tests un `FakeClock` para probar antes / exactamente en / después del cierre.
- **Tipo de cambio en 3 capas**: (1) tasa manual en BD con fecha = la oficial del sistema; (2) botón "Sugerir tasa" que consulta un proveedor externo tras la interfaz `ExchangeRateProvider` y solo rellena el campo (el usuario confirma); (3) respaldo: si el servicio falla, usar la última tasa guardada o 500 del seed. **En TODAS las pruebas se usa un proveedor falso que devuelve 500; las pruebas nunca tocan la red.**
- **Config por entorno** (`.env.example`): `DATABASE_URL` (BD limpia por prueba), `SECRET_KEY` de ejemplo, `ENV`.
- **Errores de la API** siempre `{"error": "<codigo>", "detalle": "<mensaje legible>"}` con HTTP 400/401/404/409/422, sin trazas internas.
- **UI**: limpia y consistente, Bootstrap 5 vendorizado, tablas, formularios, badges de estado, errores claros, alternador CRC/USD. Cada botón, campo, fila y mensaje lleva `data-testid` estable (Playwright).
- **Seed/reset**: `seeds/seed.py` (`python -m seeds.seed --reset`) deja la BD en el estado de referencia; expone función reutilizable por los tests.
- **Tests**: `tests/unit`, `tests/api`, `tests/e2e`. Cada módulo se entrega con sus pruebas. Resultado esperado de cualquier prueba = reglas de arriba, no "lo que parece correcto".
- **Carpetas de entrega**: `04_Evidencias/` (salidas reales, capturas, logs; nombres con ID `EV-###`) y `05_IA/` (prompts y salidas saneadas, un `IA-###.md` por intervención).

## Convenciones de IDs
`REQ-###` requisito · `CP-###` caso de prueba · `RUN-###` ejecución · `BUG-###` defecto · `RSK-###` riesgo · `EV-###` evidencia · `IA-###` intervención de IA. Python: nombres en inglés para código/tablas, mensajes de usuario en español. Tests nombrados `test_<regla>_<escenario>` con comentario `# CP-### / REQ-###`.

## Reparto del equipo
- **Iván**: rama `feat/base-datos` (config, BD con TODOS los modelos, Clock, manejo de errores, autenticación/sesión/`require_user`, plantilla base, seed), luego proveedores, tipo de cambio y rangos de aprobación.
- **Ian**: licitaciones, ofertas, evaluación y CRUD de usuarios.
- Ian depende de `feat/base-datos` (modelos, Clock, errores, auth, plantilla base): Iván la mergea primero y Ian hace pull antes de empezar.
- Ambos escriben las pruebas de sus módulos.

## REGLAS DE GIT
- **Nunca commitear ni hacer push por tu cuenta**: siempre proponer y esperar aprobación explícita. Commits SOLO a nombre del humano (git config del repo). **Jamás** `Co-Authored-By`, "Generated with Claude" ni líneas de sesión/atribución en commits ni en descripciones de PR (el uso de IA se declara en `05_IA/` y en el Excel, no en git).
- Nunca trabajar directo en `main`. Ramas desde main actualizado: `feat/<modulo>`, `test/<modulo>`, `fix/<tema>`, `chore/<tema>`, `docs/<tema>`, `lab/bug-001`.
- Formato: `tipo(modulo): descripción` en español, imperativo, máx. ~72 caracteres; tipo ∈ feat|fix|test|docs|chore|refactor. Ej.: `feat(ofertas): rechazar oferta exactamente en el cierre`.
- Commits pequeños y con sentido; cada rama >= 2 commits (típicamente código y luego pruebas). Commitear solo con pytest en verde.
- Todo entra a main por Pull Request, **sin squash** (se conserva el historial). Mergear antes de abrir la siguiente rama para que el compañero haga pull.
- Jamás commitear `.env`, bases de datos, contraseñas, tokens ni datos reales.
- **BUG-001 (defecto controlado)**: rama `lab/bug-001`; commit que introduce el defecto (tag `bug-001-defecto`) → ejecutar el caso y guardar evidencia del fallo → commit que lo corrige (tag `bug-001-fix`) → retest + 2 regresiones → PR a main. La versión final no conserva el defecto. Guardar ambos hashes.
- **Build de QA**: al estabilizar el código, tag `qa-build-1`; todas las RUN citan ese hash. Si el código cambia: nuevo tag y se anota.
- Hooks: `git config core.hooksPath .githooks` (commit-msg) + hook de Claude en `.claude/settings.json`.

## Decisiones tomadas por cuenta propia (revisar)
Ver lista al final de `docs/contrato.md` §12.
