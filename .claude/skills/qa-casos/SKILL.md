---
name: qa-casos
description: Formato de ficha de caso de prueba (CP-###) y mínimos de la práctica de QA (20 CP, 23 RUN, 8 automatizadas, BUG-001). Usar al diseñar o documentar pruebas.
---

# Fichas de casos de prueba

Cada caso lleva estos campos (el resultado esperado se deriva de `reglas-licitaciones`, nunca del código):

```
CP-###
Título:
REQ:                      (uno o más REQ-###)
Tipo/nivel:               unitaria | integración/API | funcional | seguridad | usabilidad | rendimiento
Técnica:                  partición de equivalencia | valores límite | tabla de decisión | transición de estados | caso de uso | exploratoria ...
Prioridad:                Alta | Media | Baja
Precondiciones:
Entradas exactas:         (valores literales, p. ej. presupuesto 1000000.00, oferta 1000000.01)
Pasos:
Resultado esperado:       ... (REQ de origen: REQ-###)
Modo:                     manual | automático
Origen:                   humano | IA | mixto
IA-###:                   (archivo en 05_IA/, si aplica)
Revisor:                  (lo completa el humano)
```

## Mínimos de la práctica
- **20 CP**: >= 7 unitarios, >= 3 integración/API, >= 4 funcionales, >= 2 seguridad, >= 1 usabilidad, >= 1 rendimiento, + 2 extra de borde/negativo.
- **>= 23 RUN** (ejecuciones; cada una cita el hash del tag `qa-build-N`).
- **>= 8 pruebas automatizadas**.
- **1 defecto controlado** (BUG-001) con evidencia antes/después (EV-###): ver `flujo-commits`.

Ejemplos de valores límite obligatorios: oferta = presupuesto (válida), presupuesto + 0,01 (rechaza), 0 y negativo (rechaza); oferta en `cierre − 1 s` (acepta), `cierre` exacto y `cierre + 1 s` (rechazan); ahorro 10 % exacto = Conveniente, 9,99 % = Aceptable; 999 999,99 = Encargado, 1 000 000,00 = Gerencia, 10 000 000,00 = Junta.

No inventar la revisión humana ni los resultados de ejecución: las RUN registran salidas reales (guardadas en `04_Evidencias/EV-###`).
