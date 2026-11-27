# Índice de evidencias (04_Evidencias)

Cada archivo `EV-###_*.txt` es la **salida literal** de una ejecución real. Todos citan el commit probado y el build de QA (`qa-build-1`). Las contraseñas, cookies y rutas locales no se reproducen.

## Seguridad (REQ-012) — ejecutado en la aplicación local

| EV | CP | Qué demuestra | Resultado |
|---|---|---|---|
| EV-050 | CP-015 | `POST /api/providers` con `<script>alert(1)</script>`, `Acme & Co`, `Nombre; DROP TABLE` y `Acme 😀`: los 4 se rechazan con 422 `validacion_nombre`, no se guarda nada y un nombre válido de control sí se acepta. | PASA (7/7) |
| EV-051 | CP-015 | Lo mismo desde el formulario de la UI: 422 con mensaje de error, valor reenviado escapado y sin HTML crudo; un título de licitación con `<script>` se muestra como texto en el listado y el detalle. | PASA (15/15) |
| EV-052 | CP-016 | 404, 401, 400, 405 y 422 reales, más 404/403 en la UI: formato `{error, detalle}` y sin trazas, rutas ni credenciales en ninguna respuesta. | PASA (30/30) |
| EV-053 | CP-015, CP-016 | Las pruebas pytest asociadas (29 pruebas), que incluyen el error 500 forzado con un texto "secreto" que no puede provocarse en la app sin alterar su código. | PASA (29 passed) |
| EV-054 | CP-015, CP-016 | Respaldo de build: el código de la app (`app/`, `seeds/`, `requirements.txt`) es idéntico entre el tag `qa-build-1` (`e65b2d8`) y el commit donde se ejecutó la seguridad (`cf4a817`) y `origin/main`. Guarda los hashes. | PASA (2/2) |
| EV-055 | CP-015 | Captura de la UI: el formulario de proveedor rechaza `<script>alert(1)</script>` con el mensaje de error, muestra el valor como texto y no aparece ningún diálogo. | Captura (ver imagen) |

## Registros de trabajo (para pegar en el Excel)

- `registro_ian.md`: RUN-050 (CP-015) y RUN-051 (CP-016), columnas de la hoja 06.
- `seguridad_ian.md`: SEC-001 y SEC-002, columnas de la hoja 13.

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

> Los archivos EV-050 a EV-055 los generó una herramienta de IA (ver `05_IA/IA-056.md`). La revisión humana de su contenido está pendiente.
