# Requerimientos funcionales y no funcionales

Fecha de relevamiento: 21/10/2026. Un requisito expresa un comportamiento o condición verificable; la presencia en el código no implica que todos los escenarios hayan sido probados.

## Requerimientos funcionales

| ID | Requerimiento | Evidencia en app/ | Criterio de aceptación |
| --- | --- | --- | --- |
| RF01 | Configurar tres cuentas e iniciar/cerrar sesión | auth.py; routers/auth.py | Crear usuarios distintos con contraseñas de al menos 10 caracteres; credencial incorrecta devuelve 401. |
| RF02 | Aplicar permisos de administrador, preparador y despachante | auth.exigir_roles; routers/ | Acción reservada a otro rol devuelve 403. |
| RF03 | Administrar catálogo y precios | routers/productos.py | Administrador crea/edita producto; precio positivo y stock no negativo. |
| RF04 | Consultar y buscar productos | routers/productos.py; telegram_bot.py | Buscar por texto o identificador en el panel autorizado y consultar catálogo por Telegram. |
| RF05 | Armar pedido en Telegram | telegram_bot.py | Ingresar datos, elegir cantidades y revisar antes de confirmar. |
| RF06 | Confirmar pedido con control de existencias | services/pedidos.py | Rechazar pedido sin stock; guardar detalles y descontar unidades en una operación confirmada. |
| RF07 | Calcular importe y envío | services/pedidos.py | Total = suma de precio por cantidad + envío fijo de 1500; efectivo informado debe cubrirlo. |
| RF08 | Registrar forma de pago y comprobante | schemas.py; telegram_bot.py; routers/pedidos.py | Seleccionar efectivo, transferencia o coordinar; consultar comprobante con permisos. |
| RF09 | Gestionar estados del pedido | routers/pedidos.py | Recorrer preparación, listo, en camino y entregado con el rol correspondiente. |
| RF10 | Consultar estado y cancelar por cliente | telegram_bot.py; services/cambios.py | Solo propietario cancela mientras esté pendiente; repetir no repone stock dos veces. |
| RF11 | Cancelar por administrador antes del reparto | routers/pedidos.py | Aplicar validaciones de estado; conservar pedido cancelado y reponer productos según operación. |
| RF12 | Modificar parcialmente un pedido | services/cambios.py | Quitar unidades con motivo; una pérdida no repone stock y una unidad recuperable sí. |
| RF13 | Registrar bajas e historial de inventario | routers/productos.py | Rechazar ajuste inválido; guardar motivo, autor, delta y asociación opcional al pedido. |
| RF14 | Registrar incidencias de entrega | routers/pedidos.py | Guardar novedad con motivo y permisos de reparto/administración según implementación. |
| RF15 | Notificar eventos y reintentar envíos | services/telegram.py | Registrar evento y distinguir enviado de pendiente; simular error y reintento. |
| RF16 | Marcar pago verificado manualmente | routers/pedidos.py | Operador autorizado registra la verificación después de consultar su banco. |
| RF17 | Registrar y comunicar devolución | routers/devoluciones.py; services/devoluciones.py | Administrador carga comprobante; no duplicar registro al reintentar; proteger archivo. |
| RF18 | Gestionar jornadas e historial | routers/jornadas.py | Impedir cierre con pedidos en curso; consultar jornada cerrada y sus pedidos. |
| RF19 | Crear respaldo e informe | services/backups.py; routers/respaldos.py | Generar copia SQLite y HTML en database/backups; comprobar su existencia. |
| RF20 | Consultar ventas de entregados | routers/jornadas.py; templates/index.html | Comprobar que cancelados no integran ventas de pedidos entregados. |

## Requerimientos no funcionales

| ID | Atributo | Condición | Verificación y límites |
| --- | --- | --- | --- |
| RNF01 | Seguridad de acceso | Contraseñas con PBKDF2-HMAC-SHA256, sal aleatoria y 310000 iteraciones; comparar sin almacenar texto plano. | Inspección de app/auth.py; no equivale a auditoría de seguridad. |
| RNF02 | Sesiones | Sesiones con caducidad de 12 horas, token guardado como hash y cookie HttpOnly/SameSite=Lax; Secure configurable. | Inspección de auth.py y routers/auth.py; usar Secure en HTTPS. |
| RNF03 | Persistencia | Pedidos guardados sobreviven al reinicio al conservar el archivo SQLite. | Prueba manual de reinicio con datos ficticios; pendiente de registrar en instalación del evaluador. |
| RNF04 | Integridad | Operaciones de stock y cancelaciones deben evitar duplicación por reintentos. | Pruebas aisladas de concurrencia incluidas; no hay ensayo de carga masiva. |
| RNF05 | Usabilidad | Flujo guiado por botones y panel con acciones según rol. | Recorrer caso manual; no hay estudio formal de usabilidad. |
| RNF06 | Actualización | Panel consulta periódicamente cada 30 segundos. | Inspección de templates/index.html; no es comunicación instantánea por WebSocket. |
| RNF07 | Mantenibilidad | Separación en rutas, servicios, modelos, esquemas y pruebas. | Inspección de estructura; algunas reglas permanecen en routers. |
| RNF08 | Reproducibilidad | Registrar versiones instaladas y proporcionar configuración sin secretos. | Inventario completo y archivo de versiones fijadas incluidos. |
| RNF09 | Recuperabilidad | Respaldar SQLite y documentar restauración con procesos detenidos. | Validación manual del archivo; no existe asistente automático de restauración. |
| RNF10 | Privacidad de la entrega | No incluir .env, base real, sesiones, comprobantes ni logs operativos. | Paquete construido por lista de inclusión y revisado. |
| RNF11 | Disponibilidad delimitada | Operación local mientras la PC y procesos estén activos; internet para Telegram. | Condición de operación; no se promete SLA ni 24/7. |
| RNF12 | Compatibilidad de referencia | Python 3.14.4 y SQLite 3.50.4 en Windows; navegador con HTML/CSS/JavaScript. | Entorno inspeccionado; otras combinaciones requieren validación. |

## Reglas de negocio
El carrito no reserva unidades: se revisan al confirmar. Los detalles conservan el precio del pedido. El stock disponible ya excluye unidades confirmadas. El cliente solo cancela su pedido pendiente. Las ventas se calculan sobre entregados. La revisión del pago y la devolución monetaria son humanas. La cancelación parcial se registra como modificación, no como estado adicional. El costo y zona son valores configurados en código, no un motor de tarifas o validación geográfica.
