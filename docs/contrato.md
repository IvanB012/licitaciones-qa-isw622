# Contrato técnico — Sistema de Gestión de Licitaciones

Documento común para Iván e Ian. Deriva de las reglas de negocio de `CLAUDE.md` (REQ-001…REQ-014). Si hay conflicto, mandan las reglas de negocio.

## 1. Convenciones generales
- **Dinero**: CRC en céntimos enteros (`BIGINT`) en BD; `Decimal` en código; strings decimales con punto y 2 decimales en la API (`"9000000.00"`). Se rechaza `float`/notación científica/más de 2 decimales (422).
- **Fechas/horas**: BD y API en UTC, ISO-8601 con `Z` (`2026-11-27T18:00:00Z`). La UI muestra hora de Costa Rica (UTC−6, sin DST). Todo el código obtiene la hora de `Clock.now()`.
- **Normalización de texto** (función pura `normalize_name`): `strip` + compactar espacios internos (`\s+`→` `) + `casefold`. Se guarda el nombre original recortado/compactado en `name` y la clave en `name_key` (UNIQUE).
- **Código de licitación**: `strip` + `casefold` para la clave `code_key` (UNIQUE); se guarda `code` recortado en mayúsculas del usuario.
- **Capas**: rules (puras) → services (BD) → api / web. API y UI llaman a los mismos services.

## 2. Tablas de BD (SQLite, SQLAlchemy)

### users
| campo | tipo | restricciones |
|---|---|---|
| id | INTEGER | PK |
| username | TEXT | NOT NULL, UNIQUE (casefold) |
| password_hash | TEXT | NOT NULL (argon2) |
| role | TEXT | NOT NULL, CHECK in ('admin','operador') |
| active | BOOLEAN | NOT NULL default 1 |

### providers
| id | INTEGER PK |
| name | TEXT NOT NULL (original normalizado en espacios) |
| name_key | TEXT NOT NULL **UNIQUE** (casefold) |
| contact_email | TEXT NULL |
| created_at | DATETIME NOT NULL |

### tenders
| id | INTEGER PK |
| code | TEXT NOT NULL |
| code_key | TEXT NOT NULL **UNIQUE** |
| title | TEXT NOT NULL (no vacío tras strip) |
| description | TEXT NULL |
| budget_cents | BIGINT NOT NULL, CHECK > 0 |
| closes_at | DATETIME NOT NULL (UTC) |
| status | TEXT NOT NULL, CHECK in ('Borrador','Publicada','Cerrada') default 'Borrador' |
| created_at | DATETIME NOT NULL |

### offers
| id | INTEGER PK |
| tender_id | INTEGER NOT NULL **FK → tenders.id** |
| provider_id | INTEGER NOT NULL **FK → providers.id** |
| amount_cents | BIGINT NOT NULL, CHECK > 0 |
| created_at | DATETIME NOT NULL (reloj inyectable; desempate) |
| — | **UNIQUE (tender_id, provider_id)** (REQ-006) |

### exchange_rates
| id | INTEGER PK |
| rate_x10000 | INTEGER NOT NULL, CHECK > 0 (CRC por USD ×10 000; 500,00 → 5 000 000) |
| rate_date | DATE NOT NULL (fecha oficial del sistema = fecha del `Clock`) |
| source | TEXT NOT NULL, in ('manual','sugerida','seed') |
| created_at | DATETIME NOT NULL |

### approval_ranges
| id | INTEGER PK |
| level | TEXT NOT NULL ('Encargado de área','Gerencia','Junta Directiva'; UNIQUE) |
| min_cents | BIGINT NOT NULL, >= 1 (inclusivo) |
| max_cents | BIGINT NULL (exclusivo; NULL = sin tope) |
| — | CHECK max_cents IS NULL OR max_cents > min_cents |

Relaciones: tenders 1—N offers N—1 providers. exchange_rates y approval_ranges son tablas de configuración.

## 3. Máquina de estados (REQ-003)
```
Borrador ──publicar──▶ Publicada ──cerrar──▶ Cerrada
   └──────────cerrar────────────────────────▶ Cerrada
```
Cualquier otra transición → 409 `transicion_invalida`. Publicar exige `closes_at > now` (422 `cierre_no_futuro`). "Cerrada" es terminal.
Una Publicada cuyo `closes_at <= now` sigue almacenada como Publicada pero **no acepta ofertas** (REQ-004); la UI la muestra como "Publicada (vencida)". El cierre es manual (acción cerrar), sin job en segundo plano.

## 4. Formato de errores (REQ-011/012)
Todas las respuestas de error de la API:
```json
{"error": "<codigo>", "detalle": "<mensaje legible en español>"}
```
| HTTP | Uso | Códigos |
|---|---|---|
| 400 | JSON/formato malformado | `solicitud_invalida` |
| 401 | sin sesión / credenciales malas | `no_autenticado`, `credenciales_invalidas` |
| 403 | sin permiso (rol) | `prohibido` |
| 404 | no existe | `no_encontrado` |
| 409 | conflicto de estado/unicidad | `duplicado`, `transicion_invalida`, `licitacion_no_publicada`, `licitacion_vencida`, `oferta_duplicada`, `en_uso`, `rango_traslapado`, `sin_rango_aprobacion` |
| 422 | validación | `validacion_nombre`, `validacion_codigo`, `validacion_titulo`, `monto_invalido`, `monto_excede_presupuesto`, `cierre_no_futuro`, `tasa_invalida`, `rango_invalido` |
| 500 | error interno | `error_interno` (mensaje genérico, sin traza/ruta/credenciales) |
Los errores de validación de FastAPI/Pydantic se capturan y se convierten a este formato (422). Un handler global convierte excepciones no controladas a 500 genérico.

## 5. Rutas de API (prefijo `/api`, todas requieren sesión salvo login/health)
Tipos: `money` = string decimal; `dt` = ISO UTC.

### Auth
| POST `/api/auth/login` | `{username,password}` | 200 `{username,role}` + cookie `session`; 401 `credenciales_invalidas` |
| POST `/api/auth/logout` | — | 204 |
| GET `/api/auth/me` | — | 200 `{username,role}`; 401 `no_autenticado` |
| GET `/api/health` | — | 200 `{"status":"ok"}` (sin auth) |

### Proveedores (REQ-001, 012)
| POST `/api/providers` | `{name, contact_email?}` | 201 `{id,name,contact_email}`; 422 `validacion_nombre` (carácter no permitido o vacío; permitido: letras con tildes/ñ, dígitos, espacio, `.` `,` `(` `)`); 409 `duplicado` |
| GET `/api/providers` | — | 200 `[provider]` |
| GET `/api/providers/{id}` | — | 200; 404 |
| PUT `/api/providers/{id}` | `{name, contact_email?}` | 200; 404; 422; 409 `duplicado` (ignora a sí mismo) |
| DELETE `/api/providers/{id}` | — | 204; 404; 409 `en_uso` si tiene ofertas |

### Licitaciones (REQ-002, 003)
| POST `/api/tenders` | `{code,title,description?,budget:money,closes_at:dt}` | 201 `{id,code,title,budget,closes_at,status:"Borrador"}`; 422 `validacion_codigo`/`validacion_titulo`/`monto_invalido`/`cierre_no_futuro`; 409 `duplicado` |
| GET `/api/tenders` | `?status=` | 200 `[tender]` |
| GET `/api/tenders/{id}` | — | 200; 404 |
| PUT `/api/tenders/{id}` | mismos campos | 200; solo en Borrador (si no, 409 `transicion_invalida`); mismas validaciones |
| DELETE `/api/tenders/{id}` | — | 204; 409 `en_uso` si no es Borrador o tiene ofertas |
| POST `/api/tenders/{id}/publish` | — | 200 tender Publicada; 409 `transicion_invalida`; 422 `cierre_no_futuro` |
| POST `/api/tenders/{id}/close` | — | 200 tender Cerrada; 409 `transicion_invalida` |
| GET `/api/tenders/{id}/evaluation` | `?currency=CRC\|USD` | 200 `{best_offer:{offer_id,provider_id,amount} \| null, message, savings_pct:"10.00", classification, approver, currency, rate?, rate_date?}`; sin ofertas: `best_offer:null, message:"Sin ofertas válidas"`; 409 `sin_rango_aprobacion` |

### Ofertas (REQ-004…007)
| POST `/api/tenders/{id}/offers` | `{provider_id, amount:money}` | 201 `{id,tender_id,provider_id,amount,created_at}`; 404 licitación/proveedor; 409 `licitacion_no_publicada`; 409 `licitacion_vencida` (`now >= closes_at`); 409 `oferta_duplicada`; 422 `monto_invalido` (<=0, formato) / `monto_excede_presupuesto` (> presupuesto) |
| GET `/api/tenders/{id}/offers` | — | 200 `[offer]` |
| GET `/api/offers/{id}` | — | 200; 404 |
| PUT `/api/offers/{id}` | `{amount}` | 200; mismas reglas de monto/estado/vencimiento; no cambia `created_at` |
| DELETE `/api/offers/{id}` | — | 204; 409 `licitacion_vencida`/`licitacion_no_publicada` si ya no está abierta |

Orden de validación en crear oferta: existe licitación → existe proveedor → estado Publicada → no vencida → formato/monto → duplicado. La BD respalda con UNIQUE/CHECK (violación → mismo 409/422, nunca 500).

### Tipo de cambio (REQ-010)
| POST `/api/exchange-rates` | `{rate:money-like >0, rate_date?, source?}` | 201 `{id,rate,rate_date,source}` (`source` opcional `"manual"` (defecto) \| `"sugerida"`); 422 `tasa_invalida` (<=0, formato, >4 decimales, fuente inválida). `rate_date` por defecto = fecha del Clock; debe ser la oficial (otra fecha → 422) |
| GET `/api/exchange-rates` | — | 200 lista (más reciente primero) |
| GET `/api/exchange-rates/current` | — | 200 `{rate,rate_date,source}`; respaldo última guardada, si no hay → 500.00 `source:"seed"` |
| GET `/api/exchange-rates/suggest` | — | 200 `{rate,source:"externo"}` **solo sugiere, no guarda**; si el proveedor falla → 200 `{rate:<respaldo>,source:"respaldo",aviso}` |
| GET `/api/exchange-rates/{id}` | — | 200; 404 |
| PUT `/api/exchange-rates/{id}` | `{rate,rate_date?}` | 200; 404; 422 `tasa_invalida`. La fecha debe ser la oficial o la que el registro ya tenía; la fuente no cambia |
| DELETE `/api/exchange-rates/{id}` | — | 204; 404 |

### Rangos de aprobación (REQ-009)
| POST `/api/approval-ranges` | `{level,min:money,max:money\|null}` | 201; 422 `rango_invalido` (min<0,01 o max<=min); 409 `rango_traslapado` |
| GET `/api/approval-ranges` | — | 200 ordenados por min |
| GET/PUT/DELETE `/api/approval-ranges/{id}` | PUT igual que POST | 200/204; 404; 409 `rango_traslapado`. Rol admin |

### Usuarios (rol admin)
| POST `/api/users` | `{username,password,role}` | 201 `{id,username,role}` (nunca devuelve hash); 409 `duplicado`; 422 |
| GET `/api/users`, GET `/api/users/{id}` | — | 200; 404 |
| PUT `/api/users/{id}` | `{role?,active?,password?}` | 200 |
| DELETE `/api/users/{id}` | — | 204; 409 `en_uso` si es el propio usuario en sesión |

Casos negativos mínimos comprobables (>= 4 operaciones): crear proveedor duplicado/carácter inválido; crear licitación sin título/presupuesto 0/cierre pasado; oferta = presupuesto +0,01, oferta en `closes_at`, oferta duplicada; transición Cerrada→Publicada; acceso sin sesión (401).

## 6. Rangos de aprobación y frontera (REQ-009)
Configurables en `approval_ranges`. Intervalos **semiabiertos [min, max)** en céntimos:

| Nivel | min_cents (incl.) | max_cents (excl.) | Equivale |
|---|---|---|---|
| Encargado de área | 1 | 100 000 000 | 0,01 – 999 999,99 |
| Gerencia | 100 000 000 | 1 000 000 000 | 1 000 000,00 – 9 999 999,99 |
| Junta Directiva | 1 000 000 000 | NULL | >= 10 000 000,00 |

Frontera: en céntimos no existe valor entre 999 999,99 (99 999 999) y 1 000 000,00 (100 000 000); el monto 1 000 000,00 pertenece a **Gerencia**. Como `max` de un rango es exclusivo y `min` del siguiente inclusivo, no hay hueco ni traslape. Validación al crear/editar/borrar: dos rangos se traslapan si `a.min < b.max_efectivo AND b.min < a.max_efectivo` (NULL = ∞) → 409 `rango_traslapado`. Los huecos se permiten en configuración, pero evaluar un monto sin rango → 409 `sin_rango_aprobacion`. El nivel se calcula sobre el monto de la mejor oferta válida (no el presupuesto).

## 7. Evaluación (REQ-007/008)
- Mejor oferta: `min(amount_cents)`; empate → menor `created_at`, luego menor `id`.
- Ahorro % = `(budget − best) / budget × 100` con `Decimal`, mostrado a 2 decimales (ROUND_HALF_UP); la **clasificación usa el valor exacto sin redondear**: `>= 10` Conveniente; `> 0 y < 10` Aceptable; `== 0` Válida sin ahorro.
- Sin ofertas: "Sin ofertas válidas" (sin ahorro ni aprobador).
- Moneda: `USD = CRC / rate`, `ROUND_HALF_UP` a 2 decimales. Ej.: 9 000 000,00 / 500,00 = 18 000,00.

## 8. Usuarios y sesión
- Sesión por cookie firmada (`SessionMiddleware`/itsdangerous con `SECRET_KEY`), `HttpOnly`, `SameSite=Lax`. Contraseñas con argon2.
- UI sin sesión → redirige a `/login`; API sin sesión → 401 JSON.
- Roles: `admin` (todo, incluye usuarios y rangos) y `operador` (proveedores, licitaciones, ofertas, tipo de cambio; sin usuarios/rangos → 403).
- Usuarios sintéticos del seed: `admin` / `Admin#2026-test`, `operador` / `Operador#2026-test`. (Datos ficticios, solo para pruebas.)

## 9. Rutas de UI (renderizadas en servidor)
| Ruta | Descripción |
|---|---|
| `/login`, `/logout` | autenticación |
| `/` | panel: licitaciones y resumen |
| `/providers`, `/providers/new`, `/providers/{id}/edit` | CRUD proveedores |
| `/tenders`, `/tenders/new`, `/tenders/{id}`, `/tenders/{id}/edit` | CRUD licitaciones; detalle con ofertas, evaluación, botones Publicar/Cerrar, formulario de oferta |
| `/offers/{id}/edit` | editar oferta |
| `/exchange-rates` (+ new/edit) | tipo de cambio, botón "Sugerir tasa" (rellena el campo; confirmar guarda) |
| `/approval-ranges` (+ new/edit) | rangos (admin) |
| `/users` (+ new/edit) | usuarios (admin) |
Alternador de moneda: parámetro `?currency=CRC|USD` (o cookie) solo cambia la vista; muestra tasa y fecha usadas. Mensajes de error en `data-testid="error-message"`; patrón de testids: `<entidad>-<campo>-input`, `<entidad>-submit`, `<entidad>-row-<id>`, `status-badge`, `currency-toggle`, `flash-success`, `flash-error`. La UI muestra los mismos mensajes `detalle` que la API. Plantillas con autoescape de Jinja2 activo (prohibido `|safe` sobre datos de usuario).

## 10. Reglas de borrado
- Proveedor con ofertas → 409 `en_uso`. Licitación: solo Borrador sin ofertas. Oferta: solo mientras su licitación esté Publicada y no vencida. Tipo de cambio: se puede borrar (el respaldo cubre la ausencia). Rango: borrar permitido si el resultado sigue sin traslape. Usuario: no el propio.
- No hay borrado en cascada; FK con `PRAGMA foreign_keys=ON`.

## 11. Interfaces inyectables
```python
class Clock(Protocol):
    def now(self) -> datetime: ...        # UTC aware
class SystemClock: ...                    # producción
class FakeClock: ...                      # tests; set()/advance()

class ExchangeRateProvider(Protocol):
    def get_rate(self) -> Decimal: ...    # CRC por USD; lanza ExchangeRateUnavailable si falla
class HttpExchangeRateProvider: ...       # httpx, timeout corto, solo producción
class FailingExchangeRateProvider: ...    # tests: simula 500 -> ExchangeRateUnavailable
```
Se inyectan vía dependencias de FastAPI (`get_clock`, `get_rate_provider`), sobrescribibles con `app.dependency_overrides`. `DATABASE_URL` permite una BD limpia por prueba.

## 12. Decisiones tomadas por cuenta propia (revisar)
1. Roles `admin`/`operador`; usuarios sintéticos con contraseñas de prueba fijas.
2. Intervalos semiabiertos en céntimos; huecos permitidos en configuración pero evaluar sin rango → 409.
3. "Cerrada" es manual; una Publicada vencida sigue Publicada (vista "vencida") y rechaza ofertas.
4. Reglas de borrado y de edición (§5, §10) y orden de validación de ofertas.
5. Tasa guardada ×10 000 como entero; hora CR (UTC−6) solo en presentación.
6. Tipo de cambio: `POST /api/exchange-rates` acepta `source` opcional (`manual` por defecto | `sugerida`); `seed` no se puede indicar. En la UI, "Sugerir tasa" es un POST a `/exchange-rates/suggest` que re-renderiza el formulario (sin JavaScript) con la tasa sugerida (`source` oculto = `sugerida`) o con la de respaldo y un aviso (`manual`). `HttpExchangeRateProvider` (httpx, 3 s, `EXCHANGE_RATE_URL`) solo se usa con `ENV` distinto de `test`. Al editar una tasa se admite conservar su fecha anterior. Tasas con más de 63 bits al escalar ×10 000 se rechazan (`tasa_invalida`).
