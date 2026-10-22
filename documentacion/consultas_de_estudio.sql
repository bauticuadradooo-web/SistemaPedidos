-- CONSULTAS DE SOLO LECTURA. Usar preferentemente una copia de la base.
-- No consultan hashes de contraseñas ni el contenido binario de comprobantes.

-- 1. Tablas disponibles.
SELECT name FROM sqlite_master
WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name;

-- 2. Estructura y relaciones declaradas de pedidos.
PRAGMA table_info(pedidos);
PRAGMA foreign_key_list(pedidos);
PRAGMA foreign_keys;

-- 3. Catálogo y stock disponible.
SELECT id, nombre, precio, stock FROM productos ORDER BY nombre;

-- 4. Pedidos por estado, sin datos de contacto de clientes.
SELECT id, jornada_id, estado, metodo_pago, total
FROM pedidos ORDER BY id DESC;

-- 5. Cabecera, líneas y producto: muestra cómo funciona JOIN.
SELECT p.id AS pedido, p.estado, pr.nombre AS producto,
       d.cantidad, d.precio AS precio_de_venta,
       d.cantidad * d.precio AS subtotal
FROM pedidos AS p
JOIN detalle_pedidos AS d ON d.pedido_id = p.id
JOIN productos AS pr ON pr.id = d.producto_id
ORDER BY p.id, d.id;

-- 6. Comparar el total guardado con la suma de las líneas y el envío.
-- Incluye cancelados: su total se conserva como referencia, no como venta.
SELECT p.id, p.total AS total_guardado,
       COALESCE(SUM(d.cantidad * d.precio), 0) + p.costo_envio AS total_calculado
FROM pedidos AS p
LEFT JOIN detalle_pedidos AS d ON d.pedido_id = p.id
GROUP BY p.id, p.total, p.costo_envio ORDER BY p.id;

-- 7. Cantidad de pedidos de cada estado.
SELECT estado, COUNT(*) AS cantidad FROM pedidos GROUP BY estado;

-- 8. Ventas por jornada: solo pedidos entregados.
SELECT j.id, j.fecha,
       SUM(CASE WHEN p.estado = 'entregado' THEN 1 ELSE 0 END) AS entregados,
       COALESCE(SUM(CASE WHEN p.estado = 'entregado' THEN p.total ELSE 0 END), 0) AS ventas
FROM jornadas AS j
LEFT JOIN pedidos AS p ON p.jornada_id = j.id
GROUP BY j.id, j.fecha ORDER BY j.id;

-- 9. Relación de cuentas con sesiones: no mostrar token_hash ni hashes de claves.
SELECT u.nombre_usuario, u.rol, COUNT(s.token_hash) AS sesiones_guardadas
FROM usuarios_panel AS u
LEFT JOIN sesiones_panel AS s ON s.usuario_id = u.id
GROUP BY u.id, u.nombre_usuario, u.rol;
-- La cantidad incluye sesiones vencidas que todavía no se limpiaron.

-- 10. Movimientos del inventario.
SELECT m.id, p.nombre, m.pedido_id, m.delta, m.motivo, m.autor, m.creado_en
FROM movimientos_stock AS m
JOIN productos AS p ON p.id = m.producto_id ORDER BY m.id DESC;

-- 11. Avisos guardados que aún no se confirmaron en Telegram.
SELECT id, pedido_id, tipo, notificado, creado_en
FROM eventos_pedido WHERE notificado = 0 ORDER BY id;

-- 12. Devoluciones, sin alias bancario ni bytes del comprobante.
SELECT id, pedido_id, importe, mime_type, enviado_telegram, creado_en
FROM devoluciones_pedido ORDER BY id DESC;

-- 13. Comprobar la unicidad declarada de la devolución.
PRAGMA index_list(devoluciones_pedido);
