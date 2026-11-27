# Índice de evidencias (04_Evidencias)

Cada archivo `EV-###_*.txt` es la **salida literal** de una ejecución real. Todos citan el commit probado y el build de QA (`qa-build-1`). Las contraseñas, cookies y rutas locales no se reproducen.

## Iván — ejecución de CP automáticos y suite completa, exactamente sobre el tag `qa-build-1` (`e65b2d8`)

| EV | RUN | CP | Qué demuestra | Resultado |
|---|---|---|---|---|
| EV-001 | RUN-001 | Suite | Suite completa de pytest (`pytest -v` sobre `tests/`): 928 pruebas, 0 fallidas, 0 con error. | PASA (928 passed) |
| EV-002 | RUN-002 | CP-001 | `"  tecnología   NORTE s.a. "` da la misma clave que P1; el alta se rechaza con 409 `duplicado` y la BD lo rechaza (UNIQUE). | PASA (5 pruebas) |
| EV-003 | RUN-003 | CP-007 | 9 000 000,00 CRC / 500,00 = USD 18 000,00; las tasas 0 y negativas se rechazan con 422 `tasa_invalida`. | PASA (23 pruebas) |
| EV-004 | RUN-004 | CP-013 | La vista USD muestra la oferta de P1 como $18 000,00 con tasa y fecha; los importes CRC de la BD no cambian al alternar (UI sin navegador). | PASA (3 pruebas) |
| EV-005 | RUN-005 | CP-014 | Ofertas en Borrador y Cerrada rechazadas con 409 `licitacion_no_publicada`; sin ofertas se muestra "Sin ofertas válidas" (UI/API sin navegador). | PASA (4 pruebas) |
| EV-006 | RUN-006 | CP-020 | La licitación, la oferta y la evaluación persisten al reiniciar la app. Brecha conocida: el proveedor solo se comprueba de forma indirecta. | PASA (3 pruebas) |

Cada archivo guarda la salida literal de pytest, el commit, el estado del árbol (limpio) y el entorno. Se ejecutaron en un *worktree* del tag, con el script de la rama de trabajo y **solo con los ids de Iván** para no sobrescribir las evidencias de Ian:
```powershell
git worktree add --detach ..\_tag_qa_build_1 qa-build-1
python scripts/ejecutar_cp.py ..\_tag_qa_build_1 resumen_ivan.json SUITE CP-001 CP-007 CP-013 CP-014 CP-020
git worktree remove --force ..\_tag_qa_build_1
```
(Copiar después `EV-001` a `EV-006` de `04_Evidencias/` del worktree al repositorio de trabajo. RUN-001 tarda unos 2 min 40 s.)

## E2E con Playwright (navegador real) — ejecutado en HEAD `575deaf`, con la app idéntica a la del tag `qa-build-1` (`e65b2d8`)

Los E2E (`tests/e2e/`) no existen en el tag; cada evidencia guarda el hash de HEAD, el de `qa-build-1` y la salida (vacía) de `git diff qa-build-1 HEAD --stat -- app seeds requirements.txt`.

| EV | RUN | CP | Qué demuestra | Resultado |
|---|---|---|---|---|
| EV-011 | RUN-011 | CP-011 | Login, proveedor nuevo, licitación nueva (Borrador), publicarla y ofertar con ese proveedor: mensajes y datos en pantalla. | PASA (1 prueba; 5 capturas) |
| EV-012 | RUN-012 | CP-012 | Detalle de L1: mejor oferta P1, ahorro 10 %, Conveniente, aprueba Gerencia. | PASA (1 prueba; 1 captura) |
| EV-013 | RUN-013 | CP-013 | L1 en USD: $18 000,00 con tasa y fecha; al volver a CRC los montos son los mismos y los importes guardados no cambian. | PASA (1 prueba; 3 capturas) |
| EV-014 | RUN-014 | CP-020 | Un proveedor creado sigue en el listado tras detener y volver a levantar el servidor con la misma BD (cierra la brecha de RUN-006). | PASA (1 prueba; 2 capturas) |

Capturas en `04_Evidencias/e2e/` (`EV-0xx_CP-0xx_<paso>.png`, 11 archivos). Reproducir (`python -m playwright install chromium` una sola vez):
```powershell
python scripts/ejecutar_cp.py . resumen_e2e.json RUN-011 RUN-012 RUN-013 RUN-014
pytest tests/e2e -m e2e        # o solo las pruebas, sin generar las evidencias de texto
```

## BUG-001 — defecto controlado (REQ-004), rama `lab/bug-001`

Detalle completo en `bug-001.md`. Defecto en `8d33f5b` (tag `bug-001-defecto`); corrección en `5fe825a` (tag `bug-001-fix`).

| EV | RUN | CP | Qué demuestra | Resultado |
|---|---|---|---|---|
| EV-007 | RUN-007 | CP-003 | Con el defecto, una oferta exactamente en el cierre se acepta (201 en vez de 409; la regla no lanza `Conflict`). | FALLA, como se esperaba (2 failed, 9 passed) |
| EV-015 | — (complementa RUN-007) | Suite | Suite completa con el defecto: fallan las 6 pruebas del instante exacto del cierre. | FALLA, como se esperaba (6 failed, 922 passed) |
| EV-008 | RUN-008 | CP-003 | Retest sobre el fix: T−1 s se acepta; T y T+1 s se rechazan con 409 `licitacion_vencida`. | PASA (11 pruebas) |
| EV-009 | RUN-009 | CP-002 | Regresión: `1000000.00` válido y `1000000.01` rechazado. | PASA (12 pruebas) |
| EV-010 | RUN-010 | CP-019 | Regresión: oferta de 0 y de monto negativo rechazadas. | PASA (20 pruebas) |

EV-015 no tiene RUN propio: es la salida de la suite completa sobre el commit del defecto y complementa a RUN-007.

## Seguridad (REQ-012) — ejecutado en la aplicación local

| EV | CP | Qué demuestra | Resultado |
|---|---|---|---|
| EV-050 | CP-015 | `POST /api/providers` con `<script>alert(1)</script>`, `Acme & Co`, `Nombre; DROP TABLE` y `Acme 😀`: los 4 se rechazan con 422 `validacion_nombre`, no se guarda nada y un nombre válido de control sí se acepta. | PASA (7/7) |
| EV-051 | CP-015 | Lo mismo desde el formulario de la UI: 422 con mensaje de error, valor reenviado escapado y sin HTML crudo; un título de licitación con `<script>` se muestra como texto en el listado y el detalle. | PASA (15/15) |
| EV-052 | CP-016 | 404, 401, 400, 405 y 422 reales, más 404/403 en la UI: formato `{error, detalle}` y sin trazas, rutas ni credenciales en ninguna respuesta. | PASA (30/30) |
| EV-053 | CP-015, CP-016 | Las pruebas pytest asociadas (29 pruebas), que incluyen el error 500 forzado con un texto "secreto" que no puede provocarse en la app sin alterar su código. | PASA (29 passed) |
| EV-054 | CP-015, CP-016 | Respaldo de build: el código de la app (`app/`, `seeds/`, `requirements.txt`) es idéntico entre el tag `qa-build-1` (`e65b2d8`) y el commit donde se ejecutó la seguridad (`cf4a817`) y `origin/main`. Guarda los hashes. | PASA (2/2) |
| EV-055 | CP-015 | Captura de la UI: el formulario de proveedor rechaza `<script>alert(1)</script>` con el mensaje de error, muestra el valor como texto y no aparece ningún diálogo. | Captura (ver imagen) |
| EV-065 | CP-015 | Captura de la UI: el formulario de proveedor rechaza `Acme & Co` con el mismo mensaje de error y muestra el valor como texto. | Captura (ver imagen) |
| EV-066 | CP-015 | Captura del listado de proveedores tras los dos rechazos: solo aparecen `Servicios del Valle` y `Tecnología Norte S.A.` (los del seed); no aparece ninguno de los nombres rechazados. | Captura (ver imagen) |

## Ejecución de CP unitarios y de API — ejecutado exactamente sobre el tag `qa-build-1` (`e65b2d8`)

| EV | RUN | CP | Qué demuestra | Resultado |
|---|---|---|---|---|
| EV-056 | RUN-052 | CP-003 | Ofertas antes, exactamente en y después del cierre: T−1 s se acepta; T y T+1 s se rechazan con 409 `licitacion_vencida` y no se guardan (regla pura y API con FakeClock). | PASA (11 pruebas) |
| EV-057 | RUN-053 | CP-002 | Oferta igual al presupuesto (`1000000.00`) es válida; presupuesto + 0,01 (`1000000.01`) se rechaza con 422 `monto_excede_presupuesto`. | PASA (12 pruebas) |
| EV-058 | RUN-054 | CP-019 | Oferta de `0`, `0.00` y negativos se rechaza con 422 `monto_invalido`; la BD también lo rechaza y la UI no guarda nada. | PASA (20 pruebas) |
| EV-059 | RUN-055 | CP-004 | Transiciones de estado: Borrador→Publicada, Borrador→Cerrada y Publicada→Cerrada se permiten; Cerrada→Publicada y Publicada→Borrador se rechazan con 409 `transicion_invalida`. | PASA (10 pruebas) |
| EV-060 | RUN-056 | CP-005 | Ahorro y clasificación con presupuesto ₡1 000 000,00: 900 000 → 10 % Conveniente; 950 000 → 5 % Aceptable; 1 000 000 → 0 % Válida sin ahorro. | PASA (9 pruebas) |
| EV-061 | RUN-057 | CP-006 | Aprobador en las fronteras: 999 999,99 → Encargado de área; 1 000 000,00 → Gerencia; 10 000 000,00 → Junta Directiva. | PASA (12 pruebas) |
| EV-062 | RUN-058 | CP-008 | La segunda oferta del mismo proveedor en la misma licitación da 409 `oferta_duplicada`; la BD también la rechaza y la original no cambia. | PASA (4 pruebas) |
| EV-063 | RUN-059 | CP-009 | La API rechaza código repetido (409), presupuesto 0 (422) y cierre pasado (422) con el formato `{error, detalle}`, y la UI rechaza lo mismo. | PASA (19 pruebas) |
| EV-064 | RUN-060 | CP-010 | Evaluación de L1: mejor oferta P1 (₡9 000 000,00); en un empate gana la registrada primero. | PASA (3 pruebas) |

Cada archivo guarda la salida literal de pytest, el commit, el estado del árbol (limpio) y el entorno. En RUN-052, RUN-054 y RUN-058 se añadió un test que la ficha no lista, porque el resultado esperado exige que la oferta rechazada no se guarde (o que la original no cambie); queda escrito en la nota de cada evidencia.

Reproducir (⚠️ sin hacer commits estando en el tag). Lo más seguro es un *worktree* separado, que no toca tu rama:
```powershell
git worktree add --detach ..\_tag_qa_build_1 qa-build-1
python scripts/ejecutar_cp.py ..\_tag_qa_build_1 resumen_cp.json CP-004 CP-005   # ids opcionales; sin ids ejecuta todos
git worktree remove --force ..\_tag_qa_build_1
```
(El script escribe la evidencia en `04_Evidencias/` del repo que se le indica; hay que copiarla después al repositorio de trabajo.)

## Postman — pruebas de la API (REQ-001, 002, 003, 005, 006, 007, 008, 009, 011 y 012)

| EV | Qué demuestra | Resultado |
|---|---|---|
| EV-067 | Colección completa (17 peticiones: éxitos y escenarios negativos) ejecutada con newman sobre un seed limpio, con la app del tag `qa-build-1` (`e65b2d8`). | PASA (17 requests, 53 aserciones, 0 fallidas) |
| EV-068 | Segunda ejecución de la colección sobre la **misma BD**, sin resetear: demuestra que se puede repetir. | PASA (17 requests, 53 aserciones, 0 fallidas) |

La colección está en `postman/` (ver `postman/README.md`). Cada evidencia guarda la salida literal de newman, el SHA-256 de la colección, los hashes y las versiones. Se ejecutó con la aplicación desde un *worktree* del tag y la colección desde la rama de trabajo, que no existe en el tag: por eso no hace falta comprobar el diff de la app.

Reproducir:
```powershell
python scripts/ejecutar_postman.py . http://127.0.0.1:8001 <ruta_al_worktree_del_tag> EV-067 salida.txt "titulo" "objetivo"
```
(La app debe estar levantada en esa URL con un seed limpio; ver `postman/README.md`.)

## Rendimiento (REQ-014) — ejecutado con la app del tag `qa-build-1` (`e65b2d8`)

| EV | RUN | CP | Qué demuestra | Resultado |
|---|---|---|---|---|
| EV-069 | RUN-061 | CP-018 | `GET /api/tenders` con 5 usuarios virtuales durante 30 s: 4 024 peticiones, 0 errores, **p95 = 54,59 ms** (umbral ≤ 1 500 ms), 134 req/s; CPU y RAM del servidor y configuración de la máquina. | CUMPLE |

Archivos de apoyo en `04_Evidencias/perf/`: `perf_20261126_224750_peticiones.csv` (una fila por petición), `perf_20261126_224750_recursos.csv` (CPU y RAM por segundo) y `perf_20261126_224750_resumen.json`. El p95 se recalculó desde el CSV con un método distinto al del script y coincide. Script y cómo ejecutarlo: `scripts/perf/README.md`.

## Usabilidad (REQ-013)

| EV | RUN | CP | Qué muestra | Resultado |
|---|---|---|---|---|
| EV-070 | RUN-062 | CP-017 | UX-001: el proveedor "Comercial Pacífico S.A." aparece en el listado tras crearlo | Sí |
| EV-074 | RUN-062 | CP-017 | UX-002: error real de la app (422) al escribir el monto como `8 500 000,00`: *"Monto inválido: use solo dígitos con punto decimal…"* | Obstáculo |
| EV-071 | RUN-062 | CP-017 | UX-002: la oferta de ₡8 500 000,00 ya registrada en el detalle de la licitación | Sí (tras corregir solo) |
| EV-072 | RUN-062 | CP-017 | UX-003: el proveedor "Distribuidora Central (CR)" aparece en el listado | Sí |
| EV-073 | RUN-062 | CP-017 | UX-004: la oferta de ₡9 200 000,00 ya registrada en el detalle de la licitación | Con ayuda |

Resultado: **3 de 4 tareas sin ayuda** (cumple REQ-013 en el límite). Detalle y propuestas de mejora en `usabilidad_ian.md`.

## Registros de trabajo (para pegar en el Excel)

- `registro_ivan.md`: RUN-001 a RUN-014 (suite completa, CP-001, CP-007, CP-013, CP-014 y CP-020; BUG-001: CP-003, CP-003, CP-002, CP-019; y E2E: CP-011, CP-012, CP-013 y CP-020), columnas de la hoja 06.
- `bug-001.md`: ficha del defecto controlado BUG-001.
- `registro_ian.md`: RUN-050 a RUN-062 (CP-015, CP-016, CP-003, CP-002, CP-019, CP-004, CP-005, CP-006, CP-008, CP-009, CP-010, CP-018 y CP-017 simulada), columnas de la hoja 06.
- `seguridad_ian.md`: SEC-001 y SEC-002, columnas de la hoja 13.
- `rendimiento_ian.md`: PERF-001, columnas de la hoja 15.
- `usabilidad_ian.md`: UX-001 a UX-004 (**simulada**), columnas de la hoja 14.

> **Renumeración:** estas evidencias se crearon como EV-101 a EV-104 y el registro de IA como IA-054. Se renombraron a EV-050 a EV-053 e IA-056 para respetar los rangos de IDs de Ian. Solo cambia el identificador: el contenido es el de la ejecución del 26-nov-2026 a las 21:50.

## Cómo reproducirlas

```powershell
# 1. BD temporal con el seed (no toca licitaciones.db)
$env:DATABASE_URL = "sqlite:///./seguridad_tmp.db"
python -m seeds.seed --reset
# 2. App en el puerto 8001 (en otra terminal, con la misma DATABASE_URL)
python -m uvicorn app.main:app --port 8001
# 3. Ejecutar los casos y regenerar los 4 archivos
python scripts/ejecutar_seguridad.py . http://127.0.0.1:8001
```

Los veredictos los calcula el script a partir de las respuestas reales. Para repetir la ejecución hay que resetear la BD antes (el caso crea un proveedor y una licitación de control). EV-054 se obtiene con `git diff qa-build-1 <commit> --stat -- app seeds requirements.txt` (debe salir vacío) y EV-055 es una captura manual de la UI.

> Los archivos EV-001 a EV-006, `registro_ivan.md` y la ampliación del script los generó una herramienta de IA (ver `05_IA/IA-006.md`; revisión humana pendiente). Lo mismo EV-007 a EV-010, EV-015, `bug-001.md` y el soporte de RUN-007 a RUN-010 en el script (ver `05_IA/IA-007.md`; revisión humana pendiente). Lo mismo EV-011 a EV-014, las 11 capturas de `04_Evidencias/e2e/`, las pruebas E2E y el soporte de RUN-011 a RUN-014 en el script (ver `05_IA/IA-008.md`; revisión humana pendiente).
>
> Los archivos EV-050 a EV-074, la colección de Postman y los scripts los generó una herramienta de IA: EV-067 y EV-068 y la colección (ver `05_IA/IA-054.md`), EV-069, el script de carga y `rendimiento_ian.md` (ver `05_IA/IA-055.md`), EV-050 a EV-055, EV-065 y EV-066 (ver `05_IA/IA-056.md`), EV-056 a EV-058 (ver `05_IA/IA-057.md`), EV-059 a EV-064 (ver `05_IA/IA-058.md`) y EV-070 a EV-074 con `usabilidad_ian.md` (ver `05_IA/IA-059.md`). La revisión humana consta en los campos de revisión de cada `IA-###` (IA-050 a IA-058); la de `IA-059` está pendiente.
