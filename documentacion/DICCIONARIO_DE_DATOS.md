# Diccionario de datos

Extraído de app/models.py. Las restricciones expresadas son declaraciones ORM; no se verificó la integridad de una base real.

## Pedido

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'pedidos'` |
| id | `Column(Integer, primary_key=True, index=True)` |
| jornada_id | `Column(Integer, ForeignKey('jornadas.id'), nullable=True, index=True)` |
| cliente | `Column(String, nullable=False)` |
| direccion | `Column(String, nullable=False)` |
| telefono | `Column(String, nullable=True)` |
| telegram_user_id | `Column(String, nullable=True, index=True)` |
| total | `Column(Float, nullable=False)` |
| estado | `Column(String, nullable=False, default='pendiente')` |
| metodo_pago | `Column(String, nullable=True)` |
| zona_entrega | `Column(String, nullable=True)` |
| costo_envio | `Column(Float, nullable=False, default=0)` |
| monto_efectivo | `Column(Float, nullable=True)` |
| comprobante_file_id | `Column(String, nullable=True)` |
| comprobante_mime_type | `Column(String, nullable=True)` |
| comprobante_nombre | `Column(String, nullable=True)` |
| pago_verificado | `Column(Boolean, nullable=False, default=False)` |
| alias_cliente | `Column(String(80), nullable=True)` |
| detalles | `relationship('DetallePedido', back_populates='pedido')` |
| jornada | `relationship('Jornada', back_populates='pedidos')` |

## Jornada

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'jornadas'` |
| id | `Column(Integer, primary_key=True, index=True)` |
| fecha | `Column(Date, nullable=False, index=True)` |
| iniciada_en | `Column(DateTime, nullable=False, default=datetime.now)` |
| cerrada_en | `Column(DateTime, nullable=True)` |
| cantidad_pedidos | `Column(Integer, nullable=False, default=0)` |
| total_ventas | `Column(Float, nullable=False, default=0)` |
| pedidos | `relationship('Pedido', back_populates='jornada')` |

## Producto

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'productos'` |
| id | `Column(Integer, primary_key=True, index=True)` |
| nombre | `Column(String, nullable=False)` |
| precio | `Column(Float, nullable=False)` |
| stock | `Column(Integer, nullable=False, default=0)` |
| detalles | `relationship('DetallePedido', back_populates='producto')` |

## DetallePedido

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'detalle_pedidos'` |
| id | `Column(Integer, primary_key=True, index=True)` |
| pedido_id | `Column(Integer, ForeignKey('pedidos.id'), nullable=False)` |
| producto_id | `Column(Integer, ForeignKey('productos.id'), nullable=False)` |
| cantidad | `Column(Integer, nullable=False)` |
| precio | `Column(Float, nullable=False)` |
| pedido | `relationship('Pedido', back_populates='detalles')` |
| producto | `relationship('Producto', back_populates='detalles')` |

## UsuarioPanel

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'usuarios_panel'` |
| id | `Column(Integer, primary_key=True, index=True)` |
| nombre_usuario | `Column(String(80), nullable=False, unique=True, index=True)` |
| rol | `Column(String(20), nullable=False)` |
| sal_password | `Column(String(64), nullable=False)` |
| hash_password | `Column(String(128), nullable=False)` |
| activo | `Column(Boolean, nullable=False, default=True)` |

## SesionPanel

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'sesiones_panel'` |
| token_hash | `Column(String(64), primary_key=True)` |
| usuario_id | `Column(Integer, ForeignKey('usuarios_panel.id'), nullable=False, index=True)` |
| expira_en | `Column(DateTime, nullable=False, index=True)` |
| usuario | `relationship('UsuarioPanel')` |

## MovimientoStock

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'movimientos_stock'` |
| id | `Column(Integer, primary_key=True)` |
| producto_id | `Column(Integer, ForeignKey('productos.id'), nullable=False, index=True)` |
| pedido_id | `Column(Integer, ForeignKey('pedidos.id'), nullable=True, index=True)` |
| delta | `Column(Integer, nullable=False)` |
| motivo | `Column(String(1000), nullable=False)` |
| autor | `Column(String(100), nullable=False)` |
| creado_en | `Column(DateTime, nullable=False, default=datetime.utcnow)` |

## EventoPedido

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'eventos_pedido'` |
| id | `Column(Integer, primary_key=True)` |
| pedido_id | `Column(Integer, ForeignKey('pedidos.id'), nullable=False, index=True)` |
| tipo | `Column(String(40), nullable=False)` |
| descripcion | `Column(String(2000), nullable=False)` |
| autor | `Column(String(100), nullable=False)` |
| creado_en | `Column(DateTime, nullable=False, default=datetime.utcnow)` |
| notificado | `Column(Boolean, nullable=False, default=False)` |

## DevolucionPedido

| Atributo | Definición declarada |
| --- | --- |
| __tablename__ | `'devoluciones_pedido'` |
| id | `Column(Integer, primary_key=True)` |
| pedido_id | `Column(Integer, ForeignKey('pedidos.id'), nullable=False, unique=True)` |
| alias_destino | `Column(String(80), nullable=False)` |
| importe | `Column(Numeric(14, 2), nullable=False)` |
| comprobante | `deferred(Column(LargeBinary, nullable=False))` |
| mime_type | `Column(String(40), nullable=False)` |
| nombre_archivo | `Column(String(100), nullable=False)` |
| autor | `Column(String(100), nullable=False)` |
| creado_en | `Column(DateTime, nullable=False, default=datetime.utcnow)` |
| enviado_telegram | `Column(Boolean, nullable=False, default=False)` |
| envio_iniciado_en | `Column(DateTime, nullable=True)` |
