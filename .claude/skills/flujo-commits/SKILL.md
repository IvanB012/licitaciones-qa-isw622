---
name: flujo-commits
description: Reglas de git del proyecto (ramas, formato de commit, PR sin squash, BUG-001, qa-build). Usar antes de cualquier commit, rama o PR.
---

# Reglas de git

- **Nunca commitear ni hacer push por tu cuenta**: proponer y esperar aprobación explícita. Los commits salen SOLO a nombre del humano (git config del repo). **Jamás** `Co-Authored-By`, "Generated with Claude" ni líneas de sesión/atribución en commits ni descripciones de PR. (El uso de IA se declara en `05_IA/` y en el Excel, no en git.)
- **Nunca trabajar directo en `main`.** Ramas desde main actualizado: `feat/<modulo>`, `test/<modulo>`, `fix/<tema>`, `chore/<tema>`, `docs/<tema>`, `lab/bug-001`.
- **Formato**: `tipo(modulo): descripción` en español, imperativo, máx. ~72 caracteres. Tipos: feat|fix|test|docs|chore|refactor.
  - `feat(ofertas): rechazar oferta exactamente en el cierre`
  - `test(evaluacion): cubrir empate por orden de registro`
  - `fix(rangos): tratar 1000000.00 como Gerencia`
  - `docs(contrato): documentar frontera entre rangos`
  - Mal: `Update stuff`, `feat: cosas`, cualquier mensaje con "Claude" o "Co-Authored-By".
- Commits pequeños y con sentido; cada rama >= 2 commits (típicamente código y luego pruebas). Commitear solo con pytest en verde.
- Todo entra a main por **Pull Request, sin squash** (se conserva el historial). Mergear antes de abrir la siguiente rama para que el compañero haga pull.
- Jamás commitear `.env`, bases de datos, contraseñas, tokens ni datos reales.
- **BUG-001**: rama `lab/bug-001`: commit que introduce el defecto (tag `bug-001-defecto`) → ejecutar el caso y guardar evidencia del fallo (EV-###) → commit que lo corrige (tag `bug-001-fix`) → retest + 2 regresiones → PR a main. La versión final no conserva el defecto. Guardar ambos hashes.
- **Build de QA**: al estabilizar el código, tag `qa-build-1`; todas las RUN citan ese hash. Si el código cambia: nuevo tag (`qa-build-2`…) y se anota.
- Hook local: `git config core.hooksPath .githooks`.
