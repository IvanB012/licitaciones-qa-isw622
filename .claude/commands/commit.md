---
description: Proponer un commit (con aprobación explícita)
---

1. Corré `pytest`. Si falla, PARÁ y mostrá el error; no sigas.
2. Verificá que no estés en `main` (`git branch --show-current`).
3. Mostrá `git status` y `git diff` (incluyendo `git diff --staged`). Revisá que no haya `.env`, `*.db`, secretos ni datos reales.
4. Proponé UN mensaje con el formato `tipo(modulo): descripción` (tipo ∈ feat|fix|test|docs|chore|refactor; español, imperativo, ~72 caracteres). Sin `Co-Authored-By`, sin "Claude", sin líneas de atribución.
5. ESPERÁ mi aprobación explícita. No continúes sin ella.
6. Solo entonces: `git add` de archivos específicos (nunca `git add .` ni `-A`) y `git commit -m "<mensaje>"`.
7. Nunca hagas push.
