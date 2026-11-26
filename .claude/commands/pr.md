---
description: Preparar título y descripción de PR para pegar en la web de GitHub
---

Los PR se crean a mano en la web de GitHub. No uses `gh`, no hagas push ni crees el PR.

1. Verificá que la rama actual no sea `main` y que tenga commits sobre main (`git log main..HEAD --oneline`). Si no hay, PARÁ.
2. Corré `pytest`; si no está en verde, PARÁ.
3. Generá, en bloques de texto separados y listos para copiar y pegar:
   - **Título**: formato `tipo(modulo): descripción`.
   - **Descripción** con secciones: Qué cambia · REQ cubiertos · Pruebas (qué se agregó y resultado) · Cómo probar.
4. Sin líneas de atribución de Claude, sin "Generated with", sin Co-Authored-By. Recordá: se mergea sin squash (elegir "Create a merge commit" en GitHub).
