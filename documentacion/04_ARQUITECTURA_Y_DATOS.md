# Arquitectura y base de datos

## Componentes y comunicación
Cliente → Telegram → proceso Python del bot → servicios compartidos → SQLite.
Personal → navegador (HTML/CSS/JavaScript) → API FastAPI → servicios/modelos SQLAlchemy → SQLite.
El bot utiliza long polling y servicios Python compartidos; no crea pedidos mediante llamadas HTTP a la propia API. Avisos y archivos se envían a Telegram. Panel y bot son procesos distintos que comparten configuración y base.

## Organización
app/main.py inicializa tablas, aplica ajustes de columnas y registra rutas. database.py crea engine y sesiones. models.py define entidades. schemas.py valida datos. auth.py implementa sesiones y permisos. routers/ expone operaciones HTTP. services/ reúne reglas compartidas. telegram_bot.py gestiona la conversación. templates/ contiene pantallas y lógica del navegador. static/ contiene recursos. tests/ contiene pruebas aisladas. scripts/ incluye la migración opcional a PostgreSQL.

## Entidades y relaciones
| Tabla | Finalidad | Relaciones principales |
| --- | --- | --- |
| productos | Nombre, precio y stock disponible | 1:N detalle_pedidos; 1:N movimientos_stock |
| pedidos | Cliente, entrega, total, estado, pago, Telegram y alias | N:1 jornadas; 1:N detalle_pedidos |
| detalle_pedidos | Producto, cantidad y precio registrado | N:1 pedidos; N:1 productos |
| jornadas | Fecha, apertura, cierre y resumen | 1:N pedidos |
| usuarios_panel | Usuario, rol, sal, hash y estado activo | 1:N sesiones_panel |
| sesiones_panel | Hash del token, usuario y vencimiento | N:1 usuarios_panel |
| movimientos_stock | Delta, motivo, autor y fecha | N:1 productos; pedido opcional |
| eventos_pedido | Tipo, descripción, autor y notificación | N:1 pedidos |
| devoluciones_pedido | Alias, importe, archivo, autor y estado del envío | N:1 pedidos, con unicidad por pedido |

La definición SQL completa se adjunta en esquema_sqlite.sql; el diccionario de columnas generado desde models.py está en DICCIONARIO_DE_DATOS.md. Se conserva el esquema disponible como referencia, sin extraer datos del comercio.

## Persistencia y transacciones
La ruta predeterminada es database/pedidos_comercio.db, relativa al directorio de ejecución. Hay validaciones de stock y control de escritura en servicios. No deben arrancarse copias del bot con el mismo token simultáneamente. Los datos sensibles incluyen contactos, direcciones, comprobantes y sesiones.

## Decisiones y limitaciones
SQLite simplifica una instalación local. No se ha certificado un volumen máximo de usuarios. Varias columnas de importes usan Float; las devoluciones usan Numeric(14,2). Esto se documenta como deuda técnica: unificar importes a representación decimal requeriría migración y pruebas. Los ajustes de esquema están en main.py y no constituyen un sistema completo de migraciones versionadas. Los respaldos implementados son para SQLite; PostgreSQL requiere un procedimiento distinto. No se realizó despliegue productivo ni auditoría de seguridad durante esta preparación documental.
