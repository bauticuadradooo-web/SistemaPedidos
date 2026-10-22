# Alcance y acuerdo de entrega académica

Proyecto: Dely Drinks. Fecha de corte comprometida: 04/11/2026.
Este documento define la propuesta de alcance para evaluación académica. No acredita una firma o aprobación contractual de terceros.

## Objeto
Entregar código fuente, instrucciones reproducibles y documentación de un sistema para un comercio de bebidas, con bot de Telegram y panel web por roles, utilizando SQLite como base de referencia.

## Incluido hasta el 4 de noviembre de 2026
1. Configuración inicial de tres cuentas distintas e inicio/cierre de sesión.
2. Catálogo, precios y existencias; búsqueda y bajas justificadas.
3. Carrito guiado en Telegram, captura de datos del cliente y confirmación.
4. Validación de existencias, total de productos y costo fijo de envío.
5. Estados pendiente, en preparación, listo para despacho, en camino, entregado y cancelado, sujetos a permisos.
6. Cancelación del cliente mientras esté pendiente y excepciones del administrador antes del reparto, según reglas del código.
7. Modificaciones parciales con motivo y tratamiento de reposición o pérdida.
8. Registro de incidencias del reparto y avisos por Telegram.
9. Carga/consulta de comprobantes y marca manual de pago verificado.
10. Registro de devoluciones del circuito implementado y envío/reintento del comprobante; el movimiento de dinero es externo.
11. Jornadas, consulta de historial y cierre condicionado a no tener pedidos en curso.
12. Respaldo SQLite e informe HTML; documentación de restauración manual.
13. Código y pruebas aisladas, documentación funcional/técnica e inventario de versiones.
14. Referencia al repositorio GitHub configurado y paquete académico sin datos reales.

## Fuera del alcance
Aplicación móvil nativa; varios comercios/sucursales; facturación fiscal; integración bancaria o cobro automático; validación automática de comprobantes; optimización de rutas/GPS; inteligencia artificial conversacional; gestión completa de usuarios y recuperación de contraseñas; tarifas dinámicas; alojamiento permanente con disponibilidad garantizada; restauración desde un asistente del panel; certificación de seguridad, carga o cumplimiento normativo.
PostgreSQL tiene código de conexión y migración, pero no es la plataforma validada para esta entrega. El túnel temporal de Cloudflare es opcional.

## Entregables y aceptación
| Entregable | Condición de aceptación |
| --- | --- |
| Código | app/, tests/, scripts/, configuración de ejemplo y dependencias presentes; sin secretos ni datos de clientes. |
| Ejecución | Instalación en entorno virtual, inicialización de usuarios y un pedido ficticio que recorra preparación y entrega. |
| Integridad | Rechazar existencias insuficientes; comprobar cancelación sin doble reposición mediante pruebas. |
| Permisos | Rechazar operaciones de un rol sin autorización del servidor. |
| Pruebas | Revisar el informe de ejecución incluido y sus límites. |
| Documentación | Descripción, alcance, requerimientos, arquitectura, datos, manual, bitácora e inventario accesibles desde el índice. |
| GitHub | Verificar acceso al enlace y que el commit entregado contenga el mismo material. Consultar la rama main publicada y su historial de commits. |

## Dependencias y responsabilidades
El desarrollador entrega código y documentación, revisa pruebas y prepara la copia académica. El evaluador ejecuta con datos ficticios y configura su propio bot si desea probar Telegram. El comercio es responsable de verificar acreditaciones y devolver dinero desde su cuenta. La demostración requiere PC activa; Telegram y el túnel requieren internet y disponibilidad de sus proveedores.

## Control de cambios y cronograma propuesto
21/10: relevamiento y preparación documental. 22/10–28/10: revisión del funcionamiento y datos académicos. 29/10–02/11: instalación limpia y verificación del repositorio. 03/11: comprobación final del paquete. 04/11: entrega. Estas fechas posteriores al relevamiento son planificación, no actividades ya realizadas.
Cualquier ampliación debe registrar descripción, motivo, impacto, responsable y aceptación, sin desplazar silenciosamente el alcance. La recepción por el profesor y la conformidad del equipo no se presuponen.
