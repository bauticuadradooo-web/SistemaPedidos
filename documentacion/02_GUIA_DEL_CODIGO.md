# 02 · Cómo leer y explicar el código

## Orden de estudio

Leé primero `app/models.py` para reconocer los datos. Después `app/database.py`, `app/schemas.py` y `app/services/pedidos.py`. Con eso entendés una compra. Luego seguí `app/routers/pedidos.py`, el JavaScript de `app/templates/index.html` y el bot. Dejá autenticación, devoluciones, jornadas y respaldos para la segunda lectura.

No hace falta memorizar cada línea. Para cada función deberías poder contestar: **qué recibe, qué valida, qué lee o cambia y qué devuelve**.

## 1. Punto de entrada: `app/main.py`

Uvicorn ejecuta `app.main:app`. La parte izquierda indica el módulo Python y la derecha el objeto FastAPI definido allí.

Al cargar el módulo:

1. `load_dotenv()` incorpora configuración del archivo `.env` al entorno, sin mostrarla en pantalla.
2. Se importan conexión, modelos y routers.
3. `Base.metadata.create_all(bind=engine)` crea las tablas que faltan.
4. Se inspeccionan columnas de `pedidos` y se agregan algunas de versiones anteriores con `ALTER TABLE`.
5. Se obtiene/crea una jornada y se asocian los pedidos antiguos que no tenían jornada.
6. Se crea `app = FastAPI()`, se publica la carpeta `static` y se incluyen los routers.

La ruta `GET /` consulta la sesión y entrega `index.html` o `login.html` mediante `FileResponse`. Los archivos de la carpeta llamada `templates` se sirven como HTML; no se usa un motor de plantillas Jinja en este código.

`create_all` **no modifica por sí solo tablas existentes**. Las ampliaciones actuales son migraciones manuales del arranque; un historial formal de migraciones sería una mejora futura.

## 2. Conexión: `app/database.py`

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/pedidos_comercio.db")
```

Lee una variable de entorno. Si no está definida, usa SQLite con una ruta relativa a la carpeta desde la que se ejecuta el proceso. Por eso los `.bat` primero cambian al directorio del proyecto.

| Objeto | Para qué sirve |
| --- | --- |
| `engine` | Administra conexiones con el motor de base de datos. No es una tabla ni una sesión de usuario. |
| `SessionLocal` | Fábrica de sesiones de trabajo de SQLAlchemy. Cada operación abre su propia sesión. |
| `Base` | Clase base para declarar los modelos y reunir los metadatos de tablas. |
| `normalizar_database_url()` | Adapta URLs PostgreSQL para que usen el controlador `psycopg` 3. |

`check_same_thread=False` permite usar conexiones SQLite desde los hilos empleados por la aplicación. No transforma SQLite en una base de escrituras simultáneas ilimitadas. `pool_pre_ping=True` comprueba conexiones al retirarlas del pool.

## 3. Modelos: `app/models.py`

```python
class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
```

Una clase describe una tabla. Un objeto `Producto` representa una fila. `Column` define un campo; `primary_key` identifica una fila; `nullable=False` impide guardar `NULL` en esa columna; `default` aporta un valor cuando corresponde al insertar mediante el modelo.

`ForeignKey("pedidos.id")` declara una referencia a otra tabla. `relationship()` permite recorrer objetos relacionados, por ejemplo `pedido.detalles`, y no crea por sí misma una columna adicional. `back_populates` vincula los dos lados de una relación ORM.

La guía de base de datos detalla las nueve tablas. Hay modelos sin `relationship`: se consultan explícitamente con su clave, como `EventoPedido` y `DevolucionPedido`.

## 4. Validación: `app/schemas.py`

Los esquemas Pydantic describen cómo deben llegar los datos; los modelos SQLAlchemy describen cómo se guardan.

```python
class DetallePedidoCreate(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)
```

Una cantidad cero o negativa no es válida. `PedidoCreate` reúne cliente, entrega, pago y una lista no vacía de detalles. Su `model_validator` exige monto para efectivo y comprobante para transferencia. El servicio todavía debe comprobar si el producto existe y si hay stock: eso depende de la base y no solo del formato del dato.

Otros esquemas se declaran junto a su router, por ejemplo `AjusteStock`, `CancelacionParcial` y `DevolucionRegistrar`.

## 5. Crear un pedido: `app/services/pedidos.py`

La función principal es `crear_pedido(db, datos)`.

| Paso del código | Explicación |
| --- | --- |
| `iniciar_escritura(db)` | Reserva la escritura en SQLite antes de leer existencias. |
| Acumular cantidades por `producto_id` | Evita que dos líneas del mismo producto eludan la validación del stock total. |
| Consultar productos ordenados y usar `with_for_update()` | En PostgreSQL bloquea las filas consultadas; el orden reduce posibles conflictos de bloqueo. |
| Verificar existencia y stock | Rechaza productos inexistentes o cantidades no disponibles. |
| Calcular `precio * cantidad` y sumar envío | El servidor determina el total; no confía en un total calculado por el navegador/cliente. |
| Obtener `jornada_actual(db)` | Asocia el pedido con la jornada de trabajo. |
| Crear `Pedido` y hacer `flush()` | Inserta la cabecera y obtiene el `id` antes de confirmar la transacción. |
| Crear `DetallePedido` | Guarda producto, cantidad y precio de venta de cada línea. |
| Restar stock y `commit()` | Confirma cabecera, detalles y stock en la misma transacción. |
| `refresh(pedido)` y `return pedido` | Actualiza el objeto desde la base y lo entrega al llamador. |

El precio se copia al detalle para conservar el precio al que se vendió. Si después cambia el precio del catálogo, una compra anterior mantiene su precio de línea.

La función se reutiliza desde el bot y desde el endpoint `POST /pedidos`, que está reservado al administrador.

## 6. API: `app/routers/`

Un router agrupa rutas HTTP. Un decorador como `@router.put("/pedidos/{pedido_id}/estado")` vincula una URL y un método con una función Python.

```python
db: Session = Depends(obtener_db)
usuario = Depends(exigir_roles("administrador", "preparador"))
```

`Depends` indica que FastAPI debe resolver esas dependencias antes de ejecutar la operación. La primera entrega una sesión de base; la segunda exige autenticación y uno de los roles indicados.

La función generadora de base usa `yield` y `finally: db.close()`. Entrega la sesión durante la solicitud y la cierra al terminar. **Cerrar la sesión de base no significa cerrar la sesión de usuario en el navegador.**

| Router | Responsabilidad |
| --- | --- |
| `auth.py` | Configurar las tres cuentas, iniciar/cerrar sesión y consultar el usuario actual. |
| `productos.py` | Crear/editar productos; consultar catálogo; buscar; ajustar stock con motivo; listar movimientos. |
| `pedidos.py` | Listar según rol, consultar un pedido, cambiar estado, quitar productos, registrar novedades, verificar pagos y recuperar comprobantes desde Telegram. |
| `jornadas.py` | Jornada actual, historial, pedidos archivados y cierre diario. |
| `respaldos.py` | Crear una copia de seguridad desde el panel. |
| `telegram.py` | Informar si hay token configurado y el modo del bot. No comprueba que el proceso del bot esté vivo. |
| `devoluciones.py` | Listar cancelaciones a devolver, registrar el comprobante, descargarlo y reintentar su envío. |

En `pedidos.py`, `pedido_a_dict()` prepara la respuesta según el rol. Para el preparador elimina los datos personales y los importes de los detalles. El filtro de pedidos también depende del rol.

Los estados se validan en el backend y deben avanzar en orden. Antes de salir o entregar se exige verificar una transferencia. El administrador conserva la cancelación completa excepcional antes del reparto.

Para ver las rutas de la versión que está ejecutándose, abrir `http://127.0.0.1:8000/docs`. Las operaciones protegidas requieren una sesión válida; ver su documentación no concede permisos.

## 7. Cambios e inventario: `app/services/cambios.py`

| Función | Qué resuelve |
| --- | --- |
| `iniciar_escritura()` | En SQLite emite `BEGIN IMMEDIATE` si todavía no comenzó una transacción en esa sesión. |
| `pedido_editable()` | Obtiene/bloquea el pedido, comprueba existencia y rechaza jornadas cerradas. |
| `motivo_valido()` | Quita espacios de los extremos y exige una explicación de 3 a 1000 caracteres. |
| `evento()` | Crea un registro de explicación/aviso asociado al pedido. |
| `reponer_detalles()` | Devuelve al inventario las cantidades que permanecen en el pedido y registra movimientos. |
| `cancelar_por_cliente()` | Verifica propietario y estado pendiente; repone stock, cancela y guarda un evento en una transacción. |
| `cancelar_parcial()` | Valida línea/cantidad, exige que quede algo, decide reposición y recalcula el total. |

La cancelación parcial usa `Decimal` al calcular el descuento y redondea a dos decimales, aunque el campo `Pedido.total` todavía se guarda como `Float`. Si las unidades están dañadas o faltan, el movimiento registra `delta=0` y el motivo explica la pérdida: no hubo una nueva variación del stock disponible.

## 8. El panel: `app/templates/`

`login.html` contiene el formulario de acceso y la configuración inicial. `index.html` contiene el panel, estilos y JavaScript en un mismo archivo; no usa React ni un proceso de compilación de frontend.

Funciones importantes de `index.html`:

| Función | Explicación |
| --- | --- |
| `api()` | Hace `fetch`, envía/recibe JSON, interpreta errores y redirige al acceso ante un 401. |
| `configurarVista()` | Muestra secciones y columnas correspondientes al rol. |
| `cargarTodo()` | Consulta pedidos y, según permisos, catálogo, jornadas, movimientos y devoluciones. |
| `dibujarPedidos()` / `articulosHtml()` | Construyen filas y detalles con los datos recibidos. |
| `esc()` | Escapa caracteres especiales antes de incluir texto de usuarios en HTML. |
| `actualizarEstado()` | Lee el selector y envía la solicitud `PUT` al backend. |
| `filtrarProductos()` | Filtra el catálogo cargado por nombre sin tildes o por código. |
| `abrirCambio()` | Prepara el diálogo de baja de stock, modificación parcial o novedad de delivery. |
| `dibujarDevoluciones()` / `abrirDevolucion()` | Muestran cancelaciones por transferencia y el formulario para registrar el reintegro. |

Los formularios validan para ayudar al usuario, pero el servidor vuelve a validar. Un navegador modificado podría omitir las restricciones de HTML; por eso no son la única barrera.

El temporizador llama a `cargarTodo()` cada 30 segundos si la pestaña está visible y no se está editando un campo ni hay un diálogo abierto. Es consulta periódica, no comunicación instantánea por WebSocket.

## 9. El bot: `app/telegram_bot.py`

`main()` configura una `Application` de python-telegram-bot, registra manejadores y ejecuta `run_polling()`.

Un `CommandHandler` recibe comandos como `/pedido`. Un `CallbackQueryHandler` recibe clics en botones de Telegram. Un `MessageHandler` recibe texto, imágenes o documentos según el estado.

`ConversationHandler` organiza la conversación en estados: nombre, dirección, teléfono, productos, cantidad, pago, monto en efectivo, alias de transferencia, comprobante y confirmación. Cada función devuelve el próximo estado. `ConversationHandler.END` termina ese armado.

`context.user_data['pedido']` conserva el carrito temporal de ese usuario. No es una fila de la base. Un reinicio del bot puede perder un carrito sin confirmar; el pedido confirmado queda persistido.

| Grupo de funciones | Qué hace |
| --- | --- |
| `leer_catalogo`, `texto_catalogo`, `teclado_productos`, `teclado_cantidad` | Consultar catálogo disponible y construir mensajes/botones. |
| `recibir_nombre`, `recibir_direccion`, `recibir_telefono` | Completar datos de entrega en el carrito. |
| `elegir_producto`, `ajustar_cantidad` | Modificar cantidades del carrito. |
| `elegir_pago`, `recibir_monto_efectivo`, `recibir_alias_transferencia`, `recibir_comprobante` | Reunir datos según la forma de pago. |
| `confirmar_pedido` | Convertir el carrito a `PedidoCreate` y llamar al servicio que guarda la compra. |
| `estado_cmd` | Buscar por número **y por ID de Telegram del dueño**. |
| `cancelar_pedido_cmd`, `cancelar_pedido_callback` | Pedir confirmación y volver a validar al cancelar. |
| `alias_devolucion_cmd` | Permitir al dueño informar/corregir la cuenta de origen mientras no se registró la devolución. |
| `cancelar` | Descartar el carrito en curso o derivar a la cancelación de un pedido confirmado, según el uso del comando. |

`async def` define una función asíncrona y `await` espera operaciones asíncronas. Eso no vuelve asíncrona a SQLAlchemy en este proyecto: la base sigue usando sesiones síncronas.

## 10. Autenticación: `app/auth.py` y `routers/auth.py`

Las contraseñas se guardan como hash PBKDF2-HMAC-SHA256, con sal aleatoria y 310.000 iteraciones. Al ingresar, se repite el cálculo y se compara el resultado. No se recupera la contraseña original a partir del hash.

Al crear una sesión se genera un token aleatorio. El navegador recibe ese token en una cookie `HttpOnly` y la base guarda su hash SHA-256, el usuario y el vencimiento de 12 horas.

En cada solicitud protegida se obtiene la cookie, se calcula su hash y se busca una sesión vigente con usuario activo. Después se comprueba su rol. `401` significa que no hay sesión válida; `403`, que no tiene permiso para esa acción.

La opción `Secure` depende de `PANEL_COOKIE_SECURE`. Debe revisarse al desplegar por HTTPS; activar esa opción sin HTTPS puede impedir el uso del panel desde ciertas direcciones HTTP locales.

## 11. Avisos: `app/services/telegram.py`

`notificar_estado()` y `notificar_pago_verificado()` envían mensajes usando la API de Telegram. Los routers los agregan a `BackgroundTasks` para responder al clic sin esperar la llamada de red.

`enviar_evento()` consulta un `EventoPedido`, envía su descripción y marca `notificado=True` solo si Telegram confirma el éxito. Si falla, el evento se conserva para reintentar desde el panel.

No todos los avisos tienen el mismo mecanismo: los avisos simples de estado/pago no tienen un registro persistente de reintento en este código. `BackgroundTasks` corre dentro del proceso web; no es una cola de trabajos externa.

## 12. Devoluciones: router y servicio

El router de devoluciones solo permite al administrador gestionar pedidos por transferencia cancelados por su cliente. No crea la devolución cuando se cancela: muestra el caso pendiente consultando pedidos y eventos. El registro se crea cuando se carga el comprobante de una devolución ya realizada.

`DevolucionRegistrar` exige cuenta, importe, contenido del archivo y dos confirmaciones explícitas. Se limita el tamaño a 5 MB, se admiten PDF/JPG/PNG y se comprueba su firma inicial. Esa validación no equivale a una verificación bancaria ni a un análisis antivirus completo.

Se bloquea el pedido y se revisa que no exista otro registro. Además, `devoluciones_pedido.pedido_id` es único. La cuenta enviada por el formulario debe coincidir con la guardada para evitar registrar una devolución sobre un formulario desactualizado.

`enviar_comprobante_devolucion()` reclama el envío con una actualización condicional y una marca temporal, confirma ese reclamo y llama a `sendDocument`. No mantiene un bloqueo SQLite mientras espera internet. Al terminar guarda si Telegram confirmó la recepción y libera la marca. Una marca abandonada puede recuperarse después de dos minutos.

El archivo se guarda en la base como binario y tiene carga diferida (`deferred`): consultar la lista no necesita cargar todos los comprobantes. El reintento reutiliza el registro y el archivo; no llama a un banco.

## 13. Jornadas y copias

`services/jornadas.py` busca la jornada abierta y crea una si no encuentra. `routers/jornadas.py` solo permite cerrar si todos los pedidos están entregados o cancelados. Guarda un resumen y abre la siguiente fecha de trabajo, no necesariamente la fecha del reloj si se están cerrando jornadas anteriores.

`services/backups.py` usa la API de copia de SQLite para generar un archivo consistente y consulta esa copia para crear un informe HTML. El archivo SQLite contiene todas las tablas; el HTML muestra una selección legible de pedidos y productos. No es una exportación completa de todos los eventos, cuentas y archivos.

## 14. Archivos que ayudan a ejecutar

- Los `.bat` seleccionan la carpeta y ejecutan Python con el entorno `.venv`.
- `Compartir-panel.ps1` comprueba el panel, inicia Cloudflare, obtiene una URL nueva, verifica DNS/HTTPS, la guarda y supervisa el acceso.
- `scripts/migrar_sqlite_a_postgres.py` copia datos a una PostgreSQL de destino preparada para la migración. No debe usarse como una demostración casual sobre la base real.
- `requirements.txt` enumera dependencias; `.env.example` documenta nombres de variables sin el token real.
- `tests/` verifica reglas con una base temporal y Telegram simulado. No es código que atiende pedidos.

## 15. Glosario mínimo para leer Python

| Expresión | Significado en este proyecto |
| --- | --- |
| `import` / `from … import` | Traer objetos de otro módulo. |
| `class` / `def` | Declarar una clase / una función. |
| `self` | Referencia al objeto actual dentro de métodos de una clase. |
| `str`, `int`, `bool`, `list` | Tipos: texto, entero, verdadero/falso y lista. |
| `str \| None` | Puede ser texto o no tener valor. |
| `if`, `for`, `return` | Decidir, repetir y devolver un resultado. |
| `with SessionLocal() as db` | Crear un contexto de trabajo cuya sesión se cierra al salir. |
| `try`, `except`, `finally` | Intentar una operación, manejar un error y ejecutar limpieza. |
| `raise HTTPException(...)` | Interrumpir la operación con un error HTTP controlado. |
| `[... for x in lista]` | Construir una lista recorriendo otros elementos. |
| `f"Pedido #{pedido.id}"` | Texto que inserta valores calculados. |
| `@router.get(...)` | Decorador que registra una función como endpoint. |

Para ubicar cualquier función en su archivo, usar el [índice completo](INDICE_DEL_CODIGO.md).
