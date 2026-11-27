# Usabilidad — Ian (hoja `14_Usabilidad`) — CP-017 / REQ-013


| UX ID | Fecha | Perfil anonimizado | Tarea | Criterio de éxito | Éxito (Sí / Con ayuda / No) | Tiempo (s) | Errores/obstáculos | Observaciones | Evidencia (EV-###) | Responsable |
|---|---|---|---|---|---|---|---|---|---|---|
| UX-001 | 2026-11-27 | Participante: persona ajena 1 (P.), ajena al equipo | Registrar el proveedor **Comercial Pacífico S.A.** | El proveedor aparece en el listado, sin ayuda | **Sí** | no cronometrado | Ninguno | Camino natural: menú Proveedores → Nuevo proveedor → nombre → Crear. El nombre con punto se acepta. La app muestra el listado con el proveedor | EV-070 | Ian |
| UX-002 | 2026-11-27 | Participante: persona ajena 1 (P.), ajena al equipo | Presentar una oferta de **₡8 500 000,00** con ese proveedor en **LIC-2026-001** | La oferta aparece en el detalle de la licitación, sin ayuda | **Sí** (tras corregir solo un error) | no cronometrado | **Escribió el monto tal como lo dice la tarea (`8 500 000,00`) y la app lo rechazó con 422:** *"Monto inválido: use solo dígitos con punto decimal y hasta 2 decimales (ej. 1500.00)."* Lo corrigió solo, leyendo el mensaje (`8500000.00`) | El formulario conserva el proveedor y lo escrito, y el mensaje trae un ejemplo, por eso pudo corregirlo sin ayuda. Tras registrar, la evaluación pasó a mostrar a Comercial Pacífico S.A. como mejor oferta (15,00 %, Conveniente, Gerencia) | EV-074 (error), EV-071 (resultado) | Ian |
| UX-003 | 2026-11-27 | Participante: persona ajena 2 (F.), ajena al equipo | Registrar el proveedor **Distribuidora Central (CR)** | El proveedor aparece en el listado, sin ayuda | **Sí** | no cronometrado | Ninguno | El nombre con paréntesis se acepta. La app confirma *"Proveedor Distribuidora Central (CR) creado."* | EV-072 | Ian |
| UX-004 | 2026-11-27 | Participante: persona ajena 2 (F.), ajena al equipo | Presentar una oferta de **₡9 200 000,00** con ese proveedor en **LIC-2026-001** | La oferta aparece en el detalle de la licitación, sin ayuda | **Con ayuda** | no cronometrado | No encontró dónde presentar la oferta: ni el listado de proveedores ni el de licitaciones tienen una acción "Ofertar" (solo *Editar*/*Eliminar* y *Ver*/*Editar*). **Preguntó** *"¿dónde presento la oferta?"*; el facilitador indicó *"abra la licitación"* | El formulario de oferta solo está en el **detalle** de la licitación. Con la indicación completó la tarea (`9200000.00`, imitando el ejemplo del campo) y la oferta apareció en la tabla | EV-073 | Ian |

## Conclusión (REQ-013: al menos 3 de las 4 tareas sin ayuda)

- Tareas completadas **sin ayuda**: **3 de 4** (UX-001, UX-002 y UX-003).
- Resultado: **cumple REQ-013**, justo en el límite (3 de 4).
- UX-004 cuenta como **"Con ayuda"**, por lo que **no** suma como éxito.

## Propuestas de mejora (surgen de obstáculos reales de la interfaz)

1. **Indicar el formato del monto junto al campo** de la oferta (hoy solo hay un ejemplo como *placeholder*) o aceptar el formato con espacios y coma decimal, que es el que usa la propia pantalla (`₡8 500 000,00`).
2. **Hacer visible dónde se presenta una oferta:** una acción "Ofertar" en el listado de licitaciones o un aviso en el listado de proveedores, ya que el formulario solo existe en el detalle.


## Condiciones de la prueba

- Tipo de prueba: **manual**, realizada por los participantes directamente en el navegador.
- Ejecución registrada como **RUN-062** (CP-017) en `registro_ian.md`.
- Fecha: 2026-11-27. Hora y navegador: no registrados. Participantes: dos personas reales ajenas al equipo, identificadas solo por iniciales (P. y F.); datos confirmados por Ian Angulo.
- **Limitaciones:** las tareas **no se cronometraron** (por eso la columna de tiempo dice "no cronometrado" y no hay tiempos que reportar), y no se registraron los nombres completos de los participantes ni la hora ni el navegador.
- Capturas (reales, de la sesión): EV-070 (UX-001), EV-071 (UX-002), EV-072 (UX-003), EV-073 (UX-004) y EV-074 (error del monto en UX-002). Sin datos personales.
