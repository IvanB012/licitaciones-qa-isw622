# Índice de evidencias (04_Evidencias)

Cada archivo `EV-###_*.txt` es la **salida literal** de una ejecución real. Todos citan el commit probado y el build de QA (`qa-build-1`). Las contraseñas, cookies y rutas locales no se reproducen.

## Seguridad (REQ-012) — ejecutado en la aplicación local

| EV | CP | Qué demuestra | Resultado |
|---|---|---|---|
| EV-101 | CP-015 | `POST /api/providers` con `<script>alert(1)</script>`, `Acme & Co`, `Nombre; DROP TABLE` y `Acme 😀`: los 4 se rechazan con 422 `validacion_nombre`, no se guarda nada y un nombre válido de control sí se acepta. | PASA (7/7) |
| EV-102 | CP-015 | Lo mismo desde el formulario de la UI: 422 con mensaje de error, valor reenviado escapado y sin HTML crudo; un título de licitación con `<script>` se muestra como texto en el listado y el detalle. | PASA (15/15) |
| EV-103 | CP-016 | 404, 401, 400, 405 y 422 reales, más 404/403 en la UI: formato `{error, detalle}` y sin trazas, rutas ni credenciales en ninguna respuesta. | PASA (30/30) |
| EV-104 | CP-015, CP-016 | Las pruebas pytest asociadas (29 pruebas), que incluyen el error 500 forzado con un texto "secreto" que no puede provocarse en la app sin alterar su código. | PASA (29 passed) |

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

Los veredictos los calcula el script a partir de las respuestas reales. Para repetir la ejecución hay que resetear la BD antes (el caso crea un proveedor y una licitación de control).

> Los archivos EV-101 a EV-104 los generó una herramienta de IA (ver `05_IA/IA-054.md`). La revisión humana de su contenido está pendiente.
