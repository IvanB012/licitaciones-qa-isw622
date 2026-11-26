---
description: Implementar un módulo con sus pruebas (sin commitear)
argument-hint: <módulo>
---

Módulo a implementar: $ARGUMENTS

1. Leé `CLAUDE.md` y `docs/contrato.md` (y la skill `reglas-licitaciones`).
2. Corré `git branch --show-current`. Si estás en `main`, PARÁ y pedime crear/cambiar a la rama adecuada (`feat/<modulo>`). No trabajes en main.
3. Implementá el módulo respetando las capas (rules → services → api → web), dinero en céntimos/Decimal, Clock inyectable, errores en el formato del contrato y `data-testid` en la UI.
4. Escribí sus pruebas (tests/unit, tests/api y/o tests/e2e). Los resultados esperados salen de las reglas REQ, no del código. Los tests nunca tocan la red (proveedor de tipo de cambio falso que devuelve 500).
5. Corré `pytest` y resumí: archivos creados, REQ cubiertos, resultado de las pruebas.
6. NO hagas commit ni push. Sugerí usar `/commit` y `/registrar-ia`.
