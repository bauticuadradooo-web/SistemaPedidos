-- Estructura SQLite exportada el 2026-10-19.
-- Sin filas, credenciales, datos de clientes ni comprobantes.
-- Material de estudio: no ejecutar sobre la base de trabajo existente.

-- table: detalle_pedidos
CREATE TABLE detalle_pedidos (
	id INTEGER NOT NULL, 
	pedido_id INTEGER NOT NULL, 
	producto_id INTEGER NOT NULL, 
	cantidad INTEGER NOT NULL, 
	precio FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pedido_id) REFERENCES pedidos (id), 
	FOREIGN KEY(producto_id) REFERENCES productos (id)
);

-- table: devoluciones_pedido
CREATE TABLE devoluciones_pedido (
	id INTEGER NOT NULL, 
	pedido_id INTEGER NOT NULL, 
	alias_destino VARCHAR(80) NOT NULL, 
	importe NUMERIC(14, 2) NOT NULL, 
	comprobante BLOB NOT NULL, 
	mime_type VARCHAR(40) NOT NULL, 
	nombre_archivo VARCHAR(100) NOT NULL, 
	autor VARCHAR(100) NOT NULL, 
	creado_en DATETIME NOT NULL, 
	enviado_telegram BOOLEAN NOT NULL, 
	envio_iniciado_en DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (pedido_id), 
	FOREIGN KEY(pedido_id) REFERENCES pedidos (id)
);

-- table: eventos_pedido
CREATE TABLE eventos_pedido (
	id INTEGER NOT NULL, 
	pedido_id INTEGER NOT NULL, 
	tipo VARCHAR(40) NOT NULL, 
	descripcion VARCHAR(2000) NOT NULL, 
	autor VARCHAR(100) NOT NULL, 
	creado_en DATETIME NOT NULL, 
	notificado BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pedido_id) REFERENCES pedidos (id)
);

-- table: jornadas
CREATE TABLE jornadas (
	id INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	iniciada_en DATETIME NOT NULL, 
	cerrada_en DATETIME, 
	cantidad_pedidos INTEGER NOT NULL, 
	total_ventas FLOAT NOT NULL, 
	PRIMARY KEY (id)
);

-- table: movimientos_stock
CREATE TABLE movimientos_stock (
	id INTEGER NOT NULL, 
	producto_id INTEGER NOT NULL, 
	pedido_id INTEGER, 
	delta INTEGER NOT NULL, 
	motivo VARCHAR(1000) NOT NULL, 
	autor VARCHAR(100) NOT NULL, 
	creado_en DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(producto_id) REFERENCES productos (id), 
	FOREIGN KEY(pedido_id) REFERENCES pedidos (id)
);

-- table: pedidos
CREATE TABLE pedidos (
	id INTEGER NOT NULL, 
	cliente VARCHAR NOT NULL, 
	direccion VARCHAR NOT NULL, 
	telefono VARCHAR, 
	telegram_user_id VARCHAR, 
	total FLOAT NOT NULL, 
	estado VARCHAR NOT NULL, 
	metodo_pago VARCHAR, monto_efectivo FLOAT, comprobante_file_id VARCHAR, comprobante_mime_type VARCHAR, comprobante_nombre VARCHAR, pago_verificado BOOLEAN NOT NULL DEFAULT FALSE, jornada_id INTEGER REFERENCES jornadas(id), zona_entrega VARCHAR, costo_envio FLOAT NOT NULL DEFAULT 0, alias_cliente VARCHAR(80), 
	PRIMARY KEY (id)
);

-- table: productos
CREATE TABLE productos (
	id INTEGER NOT NULL, 
	nombre VARCHAR NOT NULL, 
	precio FLOAT NOT NULL, 
	stock INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

-- table: sesiones_panel
CREATE TABLE sesiones_panel (
	token_hash VARCHAR(64) NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	expira_en DATETIME NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios_panel (id)
);

-- table: usuarios_panel
CREATE TABLE usuarios_panel (
	id INTEGER NOT NULL, 
	nombre_usuario VARCHAR(80) NOT NULL, 
	rol VARCHAR(20) NOT NULL, 
	sal_password VARCHAR(64) NOT NULL, 
	hash_password VARCHAR(128) NOT NULL, 
	activo BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

-- index: ix_detalle_pedidos_id
CREATE INDEX ix_detalle_pedidos_id ON detalle_pedidos (id);

-- index: ix_eventos_pedido_pedido_id
CREATE INDEX ix_eventos_pedido_pedido_id ON eventos_pedido (pedido_id);

-- index: ix_jornadas_fecha
CREATE INDEX ix_jornadas_fecha ON jornadas (fecha);

-- index: ix_jornadas_id
CREATE INDEX ix_jornadas_id ON jornadas (id);

-- index: ix_movimientos_stock_pedido_id
CREATE INDEX ix_movimientos_stock_pedido_id ON movimientos_stock (pedido_id);

-- index: ix_movimientos_stock_producto_id
CREATE INDEX ix_movimientos_stock_producto_id ON movimientos_stock (producto_id);

-- index: ix_pedidos_id
CREATE INDEX ix_pedidos_id ON pedidos (id);

-- index: ix_pedidos_telegram_user_id
CREATE INDEX ix_pedidos_telegram_user_id ON pedidos (telegram_user_id);

-- index: ix_productos_id
CREATE INDEX ix_productos_id ON productos (id);

-- index: ix_sesiones_panel_expira_en
CREATE INDEX ix_sesiones_panel_expira_en ON sesiones_panel (expira_en);

-- index: ix_sesiones_panel_usuario_id
CREATE INDEX ix_sesiones_panel_usuario_id ON sesiones_panel (usuario_id);

-- index: ix_usuarios_panel_id
CREATE INDEX ix_usuarios_panel_id ON usuarios_panel (id);

-- index: ix_usuarios_panel_nombre_usuario
CREATE UNIQUE INDEX ix_usuarios_panel_nombre_usuario ON usuarios_panel (nombre_usuario);
