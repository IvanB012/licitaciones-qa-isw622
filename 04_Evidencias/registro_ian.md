# Bitácora de ejecuciones (RUN) — Ian

> Borrador de trabajo con las columnas de la hoja `06_Ejecuciones`. **El Excel oficial lo llena solo Iván**, copiando de aquí.
> Rangos de Ian: `RUN-050` a `RUN-099` · `EV-050` a `EV-099`. Solo se anotan ejecuciones que realmente se hicieron.

| RUN | CP | Fecha/hora | Build/commit | Tipo | Entorno | Resultado | Resultado observado | EV | BUG | Ejecutor | CI/job | Duración | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RUN-050 | CP-015 | 2026-11-26 21:50 (UTC−6) | qa-build-1 / e65b2d8 (ejecutado sobre `main` cf4a817; código de la app idéntico, ver EV-054) | Seguridad (API, UI y automática) | Windows 11, Python 3.14.6, pytest 9.2.0, SQLite temporal con seed | Pasa | Los 4 nombres no permitidos (`<script>alert(1)</script>`, `Acme & Co`, `Nombre; DROP TABLE`, `Acme 😀`) se rechazan con 422 `validacion_nombre` por la API (7/7) y por el formulario de la UI (15/15); no se guarda ningún proveedor; el valor reenviado queda escapado y no aparece HTML crudo; un título de licitación con `<script>` se muestra como texto; la captura de la UI muestra el error y ningún diálogo; 29 pruebas de pytest asociadas en verde | EV-050, EV-051, EV-053, EV-054, EV-055 | — | Ian (ejecución asistida con IA, ver IA-056) | N/A (local) | — | El nombre válido de control (`Servicios del Pacífico (Prueba), S.A.`) se acepta con 201, lo que confirma que el validador no rechaza todo |
| RUN-051 | CP-016 | 2026-11-26 21:50 (UTC−6) | qa-build-1 / e65b2d8 (ejecutado sobre `main` cf4a817; código de la app idéntico, ver EV-054) | Seguridad (API, UI y automática) | Windows 11, Python 3.14.6, pytest 9.2.0, SQLite temporal con seed | Pasa | 404, 401, 400, 405 y 422 reales de la API y 404/403 de la UI: formato `{error, detalle}` y ninguna respuesta contiene trazas, nombres `.py`, rutas ni credenciales (30/30); el error 500 forzado devuelve un mensaje genérico (prueba de pytest, 29 en verde) | EV-052, EV-053, EV-054 | — | Ian (ejecución asistida con IA, ver IA-056) | N/A (local) | — | Un 500 real no puede provocarse en la app sin alterar su código; ese caso se cubre solo con la prueba forzada de pytest (EV-053) |

## Notas

- **Sobre el build:** la guía pide ejecutar sobre el tag. Estas dos RUN se ejecutaron sobre `main` (`cf4a817`), no sobre `qa-build-1`. Se demuestra que la app es la misma con `git diff qa-build-1 <commit> -- app seeds requirements.txt` (salida vacía): ver **EV-054**, que guarda los dos hashes.
- **Entorno de Ian** (distinto al de Iván, que usó Python 3.15.2): Windows 11, Python 3.14.6, pytest 9.2.0.
- **Duración:** no se midió por RUN; se deja "—" para no inventarla. La corrida de pytest de EV-053 tardó 13,67 s.
- **Pendiente de registrar** (aún no ejecutados): CP-002, CP-003, CP-004, CP-005, CP-006, CP-008, CP-009, CP-010, CP-019 (RUN-052 en adelante), CP-017 (usabilidad) y CP-018 (rendimiento).
