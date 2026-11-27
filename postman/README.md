# Colección de Postman — API de licitaciones

Pruebas de la API HTTP del sistema (éxitos y escenarios negativos). Datos **sintéticos**; funciona solo contra la aplicación local.

| Archivo | Contenido |
|---|---|
| `licitaciones.postman_collection.json` | Colección (formato v2.1) con 17 peticiones y 53 aserciones |
| `local.postman_environment.json` | Entorno: `base_url`, `username` y `password` (credenciales de prueba del README) |

## Preparación

La colección espera la aplicación con el **seed limpio** (la petición de evaluación usa los rangos de aprobación del seed):

```powershell
python -m seeds.seed --reset
uvicorn app.main:app          # http://127.0.0.1:8000
```

## Cómo ejecutarla

### Con la app de Postman
1. *Import* → seleccionar los dos archivos de esta carpeta.
2. Elegir el entorno **Local (127.0.0.1:8000)** (arriba a la derecha).
3. Clic derecho en la colección → **Run collection** → *Run*.

La petición `02` limpia la sesión previa, así que se puede ejecutar varias veces seguidas.

### Con newman (línea de comandos)
```powershell
npx newman run postman/licitaciones.postman_collection.json -e postman/local.postman_environment.json
```
Para otra dirección o puerto: `--env-var "base_url=http://127.0.0.1:8001"`. Para guardar la salida: `... | Tee-Object -FilePath salida.txt`.

> No se exporta el reporte JSON de newman al repositorio porque incluye los cuerpos de las peticiones (entre ellos el inicio de sesión).

## Qué verifica cada petición

Los errores deben tener exactamente `{"error", "detalle"}` y no contener trazas ni rutas internas (contrato §4).

| # | Petición | Esperado | REQ |
|---|---|---|---|
| 01 | Health | 200 `{"status": "ok"}` | REQ-011 |
| 02 | Limpiar sesión previa | 204 | — |
| 03 | Listar proveedores sin sesión | 401 `no_autenticado` | REQ-011 |
| 04 | Login con credenciales incorrectas | 401 `credenciales_invalidas` | REQ-011 |
| 05 | Login correcto | 200 con usuario y rol, sin contraseña, y cookie de sesión | REQ-011 |
| 06 | Crear proveedor | 201 | REQ-001 |
| 07 | Proveedor duplicado con otra capitalización y espacios | 409 `duplicado` | REQ-001 |
| 08 | Proveedor con `Acme & Co` | 422 `validacion_nombre` | REQ-012 |
| 09 | Crear licitación | 201, estado Borrador | REQ-002 |
| 10 | Publicar licitación | 200, estado Publicada | REQ-003 |
| 11 | Oferta válida (900000.00 de 1000000.00) | 201 | REQ-005 |
| 12 | Oferta duplicada del mismo proveedor | 409 `oferta_duplicada` | REQ-006 |
| 13 | Oferta +0,01 sobre el presupuesto | 422 `monto_excede_presupuesto` | REQ-005 |
| 14 | Oferta de cero | 422 `monto_invalido` | REQ-005 |
| 15 | Evaluación | 200: mejor oferta, ahorro 10.00 %, Conveniente, Encargado de área | REQ-007, 008, 009 |
| 16 | Cerrar licitación | 200, estado Cerrada | REQ-003 |
| 17 | Reabrir una licitación Cerrada | 409 `transicion_invalida` | REQ-003 |

## Cómo se encadenan y se repiten

- Un *pre-request script* genera un nombre de proveedor y un código de licitación **únicos por ejecución**, y los ids se encadenan con variables de colección (`provider_id`, `tender_id`, `offer_id`). Por eso la colección se puede ejecutar varias veces sobre la misma BD sin chocar con los duplicados.
- Cada ejecución crea 1 proveedor, 1 licitación y 1 oferta que no se borran.

## Evidencia de ejecución

Ver `04_Evidencias/INDICE.md`: **EV-067** (seed limpio) y **EV-068** (segunda ejecución sobre la misma BD). Se ejecutaron con la aplicación del build de QA `qa-build-1` (`e65b2d8`).
