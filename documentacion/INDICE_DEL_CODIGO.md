# Índice de clases y funciones

Generado desde los archivos Python. La línea es la del código revisado; puede cambiar si se edita el archivo.

Para entender las responsabilidades, leer primero [la guía del código](02_GUIA_DEL_CODIGO.md). Este índice sirve para ubicar cada símbolo.

## `app/__init__.py`

[Abrir archivo](../app/__init__.py)

Archivo de inicialización del paquete Python; no contiene lógica de negocio.

## `app/auth.py`

[Abrir archivo](../app/auth.py)

Autenticación y permisos del panel del comercio.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `obtener_db` | 16 | obtener_db() |
| `hash_password` | 24 | hash_password(password: str, salt: str \| None=None) |
| `verificar_password` | 30 | verificar_password(password: str, salt: str, expected_hash: str) |
| `hash_token` | 35 | hash_token(token: str) |
| `crear_sesion` | 39 | crear_sesion(db: Session, usuario: UsuarioPanel) |
| `usuario_de_sesion` | 49 | usuario_de_sesion(db: Session, token: str \| None) |
| `obtener_usuario_actual` | 61 | obtener_usuario_actual(request: Request, db: Session=Depends(obtener_db)) |
| `exigir_roles` | 71 | exigir_roles(*roles: str) |
| `exigir_roles.verificar_rol` | 72 | verificar_rol(usuario: UsuarioPanel=Depends(obtener_usuario_actual)) |

## `app/database.py`

[Abrir archivo](../app/database.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `normalizar_database_url` | 7 | normalizar_database_url(url: str) — Selecciona psycopg 3 para URLs PostgreSQL de distintos proveedores. |

## `app/main.py`

[Abrir archivo](../app/main.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `inicio` | 57 | inicio(request: Request) |

## `app/models.py`

[Abrir archivo](../app/models.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `Pedido` | 7 | Clase: Base |
| `Jornada` | 35 | Clase: Base |
| `Producto` | 48 | Clase: Base |
| `DetallePedido` | 62 | Clase: Base |
| `UsuarioPanel` | 82 | Clase: Base |
| `SesionPanel` | 93 | Clase: Base |
| `MovimientoStock` | 103 | Clase: Base |
| `EventoPedido` | 115 | Clase: Base |
| `DevolucionPedido` | 127 | Clase: Base |

## `app/routers/__init__.py`

[Abrir archivo](../app/routers/__init__.py)

Archivo de inicialización del paquete Python; no contiene lógica de negocio.

## `app/routers/auth.py`

[Abrir archivo](../app/routers/auth.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `CredencialNueva` | 23 | Clase: BaseModel |
| `ConfiguracionInicial` | 28 | Clase: BaseModel |
| `InicioSesion` | 34 | Clase: BaseModel |
| `fijar_cookie` | 39 | fijar_cookie(response: Response, request: Request, token: str) |
| `estado_configuracion` | 53 | estado_configuracion(db: Session=Depends(obtener_db)) |
| `configurar_cuentas` | 58 | configurar_cuentas(datos: ConfiguracionInicial, request: Request, response: Response, db: Session=Depends(obtener_db)) |
| `iniciar_sesion` | 97 | iniciar_sesion(datos: InicioSesion, request: Request, response: Response, db: Session=Depends(obtener_db)) |
| `cerrar_sesion` | 116 | cerrar_sesion(request: Request, response: Response, db: Session=Depends(obtener_db)) |
| `identidad_actual` | 126 | identidad_actual(usuario: UsuarioPanel=Depends(obtener_usuario_actual)) |

## `app/routers/devoluciones.py`

[Abrir archivo](../app/routers/devoluciones.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `DevolucionRegistrar` | 19 | Clase: BaseModel |
| `leer_datos` | 28 | async leer_datos(request: Request) |
| `listar` | 41 | listar(db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `registrar` | 59 | registrar(pedido_id: int, background_tasks: BackgroundTasks, _usuario=Depends(exigir_roles('administrador')), datos: DevolucionRegistrar=Depends(leer_datos), db: Session=Depends(obtener_db)) |
| `comprobante` | 91 | comprobante(devolucion_id: int, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `reenviar` | 101 | reenviar(devolucion_id: int, background_tasks: BackgroundTasks, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |

## `app/routers/jornadas.py`

[Abrir archivo](../app/routers/jornadas.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `obtener_db` | 16 | obtener_db() |
| `obtener_jornada_actual` | 25 | obtener_jornada_actual(db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `listar_jornadas_finalizadas` | 43 | listar_jornadas_finalizadas(db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `pedidos_de_jornada` | 66 | pedidos_de_jornada(jornada_id: int, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `finalizar_jornada` | 84 | finalizar_jornada(db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |

## `app/routers/pedidos.py`

[Abrir archivo](../app/routers/pedidos.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `CancelacionParcial` | 23 | Clase: BaseModel |
| `IncidenciaDelivery` | 30 | Clase: BaseModel |
| `eventos_a_dict` | 34 | eventos_a_dict(pedido) |
| `obtener_db` | 43 | obtener_db() |
| `crear_pedido` | 52 | crear_pedido(pedido: PedidoCreate, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `pedido_a_dict` | 60 | pedido_a_dict(pedido: Pedido, rol: str) |
| `listar_pedidos` | 101 | listar_pedidos(db: Session=Depends(obtener_db), usuario=Depends(exigir_roles('administrador', 'preparador', 'despachante'))) |
| `obtener_pedido` | 115 | obtener_pedido(pedido_id: int, db: Session=Depends(obtener_db), usuario=Depends(exigir_roles('administrador', 'despachante'))) |
| `cambiar_estado` | 127 | cambiar_estado(pedido_id: int, nuevo_estado: str, background_tasks: BackgroundTasks, db: Session=Depends(obtener_db), usuario=Depends(exigir_roles('administrador', 'preparador', 'despachante'))) |
| `quitar_productos` | 182 | quitar_productos(pedido_id: int, datos: CancelacionParcial, background_tasks: BackgroundTasks, db: Session=Depends(obtener_db), usuario=Depends(exigir_roles('administrador', 'preparador'))) |
| `informar_delivery` | 191 | informar_delivery(pedido_id: int, datos: IncidenciaDelivery, background_tasks: BackgroundTasks, db: Session=Depends(obtener_db), usuario=Depends(exigir_roles('administrador', 'despachante'))) |
| `reenviar_aviso` | 203 | reenviar_aviso(pedido_id: int, evento_id: int, background_tasks: BackgroundTasks, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador', 'preparador', 'despachante'))) |
| `verificar_pago` | 213 | verificar_pago(pedido_id: int, background_tasks: BackgroundTasks, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador', 'despachante'))) |
| `obtener_comprobante` | 234 | obtener_comprobante(pedido_id: int, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador', 'despachante'))) |

## `app/routers/productos.py`

[Abrir archivo](../app/routers/productos.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `ProductoCrear` | 14 | Clase: BaseModel |
| `ProductoActualizar` | 20 | Clase: BaseModel |
| `AjusteStock` | 26 | Clase: BaseModel |
| `obtener_db` | 32 | obtener_db() |
| `crear_producto` | 42 | crear_producto(producto: ProductoCrear, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `listar_productos` | 61 | listar_productos(db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador', 'preparador')), q: str='') |
| `listar_productos.normalizar` | 68 | normalizar(texto) |
| `actualizar_producto` | 77 | actualizar_producto(producto_id: int, datos: ProductoActualizar, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))) |
| `ajustar_stock` | 101 | ajustar_stock(producto_id: int, ajuste: AjusteStock, background_tasks: BackgroundTasks, db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador', 'preparador'))) |
| `historial_stock` | 140 | historial_stock(db: Session=Depends(obtener_db), _usuario=Depends(exigir_roles('administrador', 'preparador'))) |

## `app/routers/respaldos.py`

[Abrir archivo](../app/routers/respaldos.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `crear_copia` | 10 | crear_copia(_usuario=Depends(exigir_roles('administrador'))) |

## `app/routers/telegram.py`

[Abrir archivo](../app/routers/telegram.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `estado_bot` | 9 | estado_bot() |

## `app/schemas.py`

[Abrir archivo](../app/schemas.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `DetallePedidoCreate` | 5 | Clase: BaseModel |
| `PedidoCreate` | 10 | Clase: BaseModel |
| `PedidoCreate.validar_datos_pago` | 25 | validar_datos_pago(self) |

## `app/services/__init__.py`

[Abrir archivo](../app/services/__init__.py)

Archivo de inicialización del paquete Python; no contiene lógica de negocio.

## `app/services/backups.py`

[Abrir archivo](../app/services/backups.py)

Creación de copias consistentes de la base SQLite del comercio.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `crear_informe_pedidos` | 10 | crear_informe_pedidos(copia: Path) — Crea junto a una copia SQLite un informe de pedidos fácil de leer. |
| `crear_informe_pedidos.celda` | 35 | celda(valor) |
| `crear_informe_pedidos.dinero` | 38 | dinero(valor) |
| `crear_respaldo` | 68 | crear_respaldo() |

## `app/services/cambios.py`

[Abrir archivo](../app/services/cambios.py)

Cambios de pedidos e inventario serializados con registro del motivo.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `iniciar_escritura` | 10 | iniciar_escritura(db) |
| `pedido_editable` | 17 | pedido_editable(db, pedido_id) |
| `motivo_valido` | 28 | motivo_valido(motivo) |
| `evento` | 35 | evento(db, pedido, tipo, descripcion, autor) |
| `reponer_detalles` | 42 | reponer_detalles(db, pedido, autor, motivo) |
| `cancelar_por_cliente` | 52 | cancelar_por_cliente(db, pedido_id, telegram_id) |
| `cancelar_parcial` | 69 | cancelar_parcial(db, pedido_id, detalle_id, cantidad, motivo, reponer_stock, autor) |

## `app/services/devoluciones.py`

[Abrir archivo](../app/services/devoluciones.py)

Registro de devoluciones ya hechas por el comercio y envío del recibo.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `validar_alias` | 15 | validar_alias(valor) |
| `guardar_alias_cliente` | 23 | guardar_alias_cliente(db, pedido_id, telegram_id, alias) |
| `cancelado_por_cliente` | 37 | cancelado_por_cliente(db, pedido) |
| `enviar_comprobante_devolucion` | 42 | enviar_comprobante_devolucion(devolucion_id) |

## `app/services/jornadas.py`

[Abrir archivo](../app/services/jornadas.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `jornada_actual` | 8 | jornada_actual(db: Session) — Devuelve la jornada abierta; si no hay ninguna, abre la siguiente fecha. |

## `app/services/pedidos.py`

[Abrir archivo](../app/services/pedidos.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `crear_pedido` | 12 | crear_pedido(db: Session, datos: PedidoCreate) |

## `app/services/telegram.py`

[Abrir archivo](../app/services/telegram.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `enviar_evento` | 19 | enviar_evento(evento_id: int) — Conserva el aviso pendiente si Telegram falla; el panel permite reintentar. |
| `notificar_estado` | 48 | notificar_estado(chat_id: str \| None, pedido_id: int, estado: str) — Notifica al cliente cuando el comercio cambia el estado del pedido. |
| `notificar_pago_verificado` | 72 | notificar_pago_verificado(chat_id: str \| None, pedido_id: int) — Informa al cliente que el comercio revisó el comprobante de transferencia. |

## `app/telegram_bot.py`

[Abrir archivo](../app/telegram_bot.py)

Bot de pedidos con long polling. Ejecutar con python -m app.telegram_bot.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `leer_catalogo` | 36 | leer_catalogo() |
| `precio_texto` | 41 | precio_texto(precio) |
| `alias_transferencia` | 45 | alias_transferencia() |
| `total_y_lineas` | 49 | total_y_lineas(pedido) |
| `enviar_resumen` | 65 | async enviar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE, editar=False) |
| `cantidad_en_pedido` | 103 | cantidad_en_pedido(pedido, producto_id) |
| `teclado_productos` | 110 | teclado_productos(pedido=None) |
| `teclado_cantidad` | 136 | teclado_cantidad(cantidad, maximo, ya_agregado=False) |
| `cantidad_maxima_disponible` | 153 | cantidad_maxima_disponible(producto, pedido) |
| `editar_catalogo` | 157 | async editar_catalogo(update, context) |
| `texto_catalogo` | 186 | texto_catalogo(incluir_bienvenida=False) |
| `teclado_inicio_pedido` | 198 | teclado_inicio_pedido() |
| `start` | 202 | async start(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `productos_cmd` | 206 | async productos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `responder_mensaje_libre` | 210 | async responder_mensaje_libre(update: Update, context: ContextTypes.DEFAULT_TYPE) — Ante un saludo o texto fuera del flujo, ofrece el catálogo sin comandos. |
| `estado_cmd` | 221 | async estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `boton_cancelacion` | 243 | boton_cancelacion(pedido_id) |
| `cancelar_pedido_cmd` | 247 | async cancelar_pedido_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `cancelar_pedido_callback` | 272 | async cancelar_pedido_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `instrucciones_devolucion` | 305 | instrucciones_devolucion(pedido) |
| `alias_devolucion_cmd` | 314 | async alias_devolucion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `iniciar_pedido` | 327 | async iniciar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `recibir_nombre` | 338 | async recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `recibir_direccion` | 344 | async recibir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `recibir_telefono` | 350 | async recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `mostrar_catalogo` | 356 | async mostrar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `elegir_producto` | 369 | async elegir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `ajustar_cantidad` | 421 | async ajustar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `elegir_pago` | 474 | async elegir_pago(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `recibir_alias_transferencia` | 503 | async recibir_alias_transferencia(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `recibir_monto_efectivo` | 514 | async recibir_monto_efectivo(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `recibir_comprobante` | 528 | async recibir_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `confirmar_pedido` | 560 | async confirmar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `cancelar` | 583 | async cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) |
| `main` | 592 | main() |

## `scripts/generar_documentacion.py`

[Abrir archivo](../scripts/generar_documentacion.py)

Exporta índice de código, esquema sin filas y diagrama para estudiar el proyecto.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `indice_codigo` | 17 | indice_codigo() |
| `esquema_sqlite` | 58 | esquema_sqlite(base=None) |
| `diagrama` | 74 | diagrama() |

## `scripts/generar_guia_html.py`

[Abrir archivo](../scripts/generar_guia_html.py)

Convierte las cinco guías propias a un documento HTML de lectura e impresión.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `inline` | 14 | inline(texto) |
| `inline.guardar` | 16 | guardar(html) |
| `markdown` | 28 | markdown(texto) |
| `generar` | 104 | generar() |

## `scripts/migrar_sqlite_a_postgres.py`

[Abrir archivo](../scripts/migrar_sqlite_a_postgres.py)

Copia datos locales a una base PostgreSQL vacía, conservando sus IDs.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `migrar` | 20 | migrar() |

## `tests/__init__.py`

[Abrir archivo](../tests/__init__.py)

Archivo de inicialización del paquete Python; no contiene lógica de negocio.

## `tests/test_cambios.py`

[Abrir archivo](../tests/test_cambios.py)

Pruebas aisladas: no leen la base real ni envían mensajes a clientes.

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `CambiosTest` | 29 | Clase: unittest.TestCase |
| `CambiosTest.setUp` | 30 | setUp(self) |
| `CambiosTest.nuevo_pedido` | 43 | nuevo_pedido(self, transferencia=False) |
| `CambiosTest.login` | 51 | login(self, rol) |
| `CambiosTest.detalle` | 54 | detalle(self, pedido_id=None) |
| `CambiosTest.parcial` | 58 | parcial(self, **overrides) |
| `CambiosTest.test_preparador_baja_y_busqueda` | 63 | test_preparador_baja_y_busqueda(self) |
| `CambiosTest.test_limites_y_roles_stock` | 76 | test_limites_y_roles_stock(self) |
| `CambiosTest.test_parcial_perdida_sin_doble_descuento` | 87 | test_parcial_perdida_sin_doble_descuento(self) |
| `CambiosTest.test_parcial_reposicion_y_linea_completa` | 101 | test_parcial_reposicion_y_linea_completa(self) |
| `CambiosTest.test_parcial_validacion_pertenencia_y_archivo` | 111 | test_parcial_validacion_pertenencia_y_archivo(self) |
| `CambiosTest.test_parcial_transferencia_registra_reintegro` | 121 | test_parcial_transferencia_registra_reintegro(self) |
| `CambiosTest.test_delivery_motivo_y_roles` | 128 | test_delivery_motivo_y_roles(self) |
| `CambiosTest.test_cliente_propietario_solo_pendiente` | 142 | test_cliente_propietario_solo_pendiente(self) |
| `CambiosTest.test_preparacion_bloquea_cancelacion_y_retroceso` | 156 | test_preparacion_bloquea_cancelacion_y_retroceso(self) |
| `CambiosTest.test_cancelacion_concurrente_no_duplica_stock` | 166 | test_cancelacion_concurrente_no_duplica_stock(self) |
| `CambiosTest.test_cancelacion_concurrente_no_duplica_stock.cancelar` | 167 | cancelar() |
| `CambiosTest.test_telegram_reintento_y_confirmacion` | 180 | test_telegram_reintento_y_confirmacion(self) |
| `CambiosTest.test_bot_confirmacion_revalida_estado` | 194 | test_bot_confirmacion_revalida_estado(self) |

## `tests/test_devoluciones.py`

[Abrir archivo](../tests/test_devoluciones.py)

| Símbolo | Línea | Descripción o firma |
| --- | --- | --- |
| `DevolucionesTest` | 21 | Clase: unittest.TestCase |
| `DevolucionesTest.setUp` | 25 | setUp(self) |
| `DevolucionesTest.datos` | 33 | datos(self, **overrides) |
| `DevolucionesTest.registrar` | 40 | registrar(self, **overrides) |
| `DevolucionesTest.test_aparece_automaticamente_y_persiste_al_archivar` | 43 | test_aparece_automaticamente_y_persiste_al_archivar(self) |
| `DevolucionesTest.test_guarda_recibo_y_no_duplica` | 54 | test_guarda_recibo_y_no_duplica(self) |
| `DevolucionesTest.test_permisos_y_recibo_protegido` | 69 | test_permisos_y_recibo_protegido(self) |
| `DevolucionesTest.test_formato_tamano_e_importe` | 78 | test_formato_tamano_e_importe(self) |
| `DevolucionesTest.test_sin_alias_y_cancelacion_no_del_cliente` | 93 | test_sin_alias_y_cancelacion_no_del_cliente(self) |
| `DevolucionesTest.test_alias_solo_propietario_e_inmutable_tras_registro` | 104 | test_alias_solo_propietario_e_inmutable_tras_registro(self) |
| `DevolucionesTest.test_envio_archivo_correcto_y_reintento_sin_nueva_devolucion` | 117 | test_envio_archivo_correcto_y_reintento_sin_nueva_devolucion(self) |
| `DevolucionesTest.test_no_reclama_envio_en_curso_y_recupera_abandonado` | 134 | test_no_reclama_envio_en_curso_y_recupera_abandonado(self) |
| `DevolucionesTest.test_bot_guarda_cuenta_para_pedido_anterior` | 148 | test_bot_guarda_cuenta_para_pedido_anterior(self) |
| `DevolucionesTest.test_bot_pide_alias_antes_del_comprobante` | 157 | test_bot_pide_alias_antes_del_comprobante(self) |
| `DevolucionesTest.test_dos_registros_concurrentes_guardan_un_solo_recibo` | 164 | test_dos_registros_concurrentes_guardan_un_solo_recibo(self) |
| `DevolucionesTest.test_dos_registros_concurrentes_guardan_un_solo_recibo.guardar` | 167 | guardar() |
| `DevolucionesTest.test_migracion_agrega_alias_sin_perder_pedidos` | 180 | test_migracion_agrega_alias_sin_perder_pedidos(self) |
