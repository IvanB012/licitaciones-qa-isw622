---
name: reglas-licitaciones
description: Reglas de negocio REQ-001..REQ-014 del Sistema de Gestión de Licitaciones y datos semilla. Usar al escribir código, casos de prueba o resultados esperados.
---

# Reglas de negocio (fuente de verdad)

**El resultado esperado de cualquier prueba sale de estas reglas, nunca de lo que "parece correcto" ni de lo que hace el código actual.** Si el código contradice una regla, el código está mal. No inventar reglas.

- **REQ-001 Proveedores**: crear/editar/listar. Nombres equivalentes (recortar espacios, compactar espacios internos, sin distinguir mayúsculas) se rechazan como duplicados.
- **REQ-002 Licitaciones**: código único sin distinguir mayúsculas ni espacios laterales; título no vacío; presupuesto CRC > 0; fecha/hora de cierre futura al crear/publicar.
- **REQ-003 Estados**: solo Borrador→Publicada, Borrador→Cerrada y Publicada→Cerrada. No volver de Publicada a Borrador ni reabrir una Cerrada.
- **REQ-004 Vencimiento**: solo se aceptan ofertas en licitaciones Publicadas y antes del instante de cierre; EXACTAMENTE en el instante de cierre se rechaza (now >= cierre rechaza).
- **REQ-005 Montos**: oferta > 0 y <= presupuesto CRC. Igual al presupuesto es válida; cero, negativo o superior se rechazan (un céntimo por encima se rechaza).
- **REQ-006 Duplicados**: un proveedor solo puede presentar una oferta por licitación; también debe rechazarlo la base de datos (restricción UNIQUE).
- **REQ-007 Mejor oferta**: gana la menor oferta válida en CRC; en empate gana la registrada primero; sin ofertas se muestra "Sin ofertas válidas".
- **REQ-008 Ahorro** = ((presupuesto − mejor oferta) / presupuesto) × 100. >= 10 %: "Conveniente"; > 0 y < 10 %: "Aceptable"; 0 %: "Válida sin ahorro".
- **REQ-009 Aprobación** por rangos CONFIGURABLES (tabla en BD, sin traslape, validado): 0,01–999 999,99 = Encargado de área; 1 000 000–9 999 999,99 = Gerencia; >= 10 000 000 = Junta Directiva. El nivel se determina sobre el monto de la mejor oferta válida. Frontera: semiabierto [min, max) en céntimos para no dejar huecos (1 000 000,00 = Gerencia).
- **REQ-010 Moneda**: solo se persisten importes en CRC; USD = CRC / (CRC por USD) con tasa > 0; mostrar tasa y fecha usadas; alternar la vista CRC/USD NO modifica la BD.
- **REQ-011 Persistencia/API**: los datos persisten al reiniciar; la API devuelve respuestas verificables (éxito y error) y NO acepta valores que la UI no aceptaría (mismas validaciones en ambas).
- **REQ-012 Seguridad**: rechazar en el nombre de proveedor caracteres que no sean letras (con tildes y ñ), números, espacios, punto, coma y paréntesis; evitar ejecución de HTML/script (escape en plantillas); ocultar errores internos (sin trazas ni rutas ni credenciales).
- **REQ-013 Usabilidad**: con dos personas ajenas, al menos 3 de 4 tareas (registrar proveedor y ofertar) se completan sin ayuda.
- **REQ-014 Rendimiento**: 5 usuarios virtuales, 30 s, GET de listado en local: p95 <= 1500 ms y error <= 5 %.

## Datos semilla
- Proveedor P1 "Tecnología Norte S.A."; Proveedor P2 "Servicios del Valle".
- Licitación L1: LIC-2026-001, presupuesto CRC 10 000 000,00, cierre = ahora + 48 h, Publicada.
- Ofertas L1: P1 = 9 000 000,00; P2 = 9 500 000,00 → gana P1, ahorro 10 %, aprueba Gerencia.
- Tipo de cambio CRC 500,00 por USD (fecha actual) → P1 = USD 18 000,00.
- Escenario aislado: presupuesto 1 000 000,00 con ofertas 900 000 / 950 000 / 1 000 000 (ahorros 10 %, 5 %, 0 %).

Detalle técnico (tablas, API, errores): `docs/contrato.md`.
