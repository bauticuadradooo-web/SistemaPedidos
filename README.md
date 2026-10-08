# Sistema de pedidos Dely Drinks

Aplicación local para que clientes pidan por Telegram y el comercio prepare y despache los pedidos desde un panel. Los pedidos, productos, cuentas y sesiones del panel se guardan en `database/pedidos_comercio.db`; apagar la computadora detiene los procesos, pero no borra esos datos.

## Primera apertura

1. Abrí esta carpeta en Visual Studio Code y asegurate de que exista `.venv` y estén instaladas las dependencias desde `requirements.txt`.
2. En Telegram, creá el bot con `@BotFather` y guardá `TELEGRAM_BOT_TOKEN` en `.env`. No compartas ese archivo.
3. Iniciá el panel con **Iniciar panel.bat** y abrí <http://127.0.0.1:8000>.
4. La primera vez, la página te pide crear tres usuarios distintos: administrador, preparador y despachante. Cada contraseña debe tener al menos 10 caracteres. Guardalas: no se pueden recuperar desde el panel.

## Roles del panel

- **Administrador:** ve todos los pedidos, las ventas entregadas, los ingresos y el catálogo; puede editar nombres, precios y stock.
- **Preparador:** ve solo los productos y cantidades; puede marcar el pedido en preparación y dejarlo listo para despacho.
- **Despachante:** ve los pedidos listos o en camino con nombre, dirección, teléfono, forma de pago y cambio; puede marcarlos en camino o entregados.
- El administrador puede cancelar un pedido antes de que salga a reparto; el stock de sus productos vuelve a estar disponible. Los pedidos cancelados no se cuentan como ventas ni impiden finalizar el día.

Las ventas e ingresos del administrador corresponden a la jornada abierta y se actualizan cada 30 segundos. El historial de pedidos entregados queda dentro de esa jornada.

## Cierre y archivo diario

- El administrador usa **Finalizar día** cuando todos los pedidos están entregados o cancelados. Si queda alguno en curso, el panel informa cuántos faltan y no permite cerrar la jornada.
- Al finalizar, se guardan la fecha, la cantidad de pedidos y las ventas. La jornada siguiente queda abierta con la fecha del día siguiente y empieza con la lista de pedidos vacía.
- Al cerrar el día se crea automáticamente una copia de la base. También se puede crear una manual desde **Copia de seguridad**. Los archivos se guardan en `database/backups`; conviene copiar periódicamente esa carpeta a un pendrive o almacenamiento externo. La copia no incluye `.env` ni el token del bot.
- En **Días finalizados**, el administrador puede abrir cada fecha para consultar sus pedidos, clientes, artículos, pagos y comprobantes. Los productos y el stock continúan al día siguiente.
- La versión anterior no guardaba fechas de los pedidos. Al activar esta función, los registros existentes se conservan en la primera jornada creada; la fecha de esa jornada no representa necesariamente la fecha real en que se hicieron esos pedidos.

## Iniciar el sistema

Para iniciar el panel y el bot juntos, hacé doble clic en **Iniciar sistema.bat**. Se abrirán dos ventanas negras y el panel en el navegador. Dejalas abiertas mientras quieras atender pedidos. También podés iniciar panel y bot por separado con los archivos de abajo.

Panel del comercio:

```powershell
& ".\Iniciar panel.bat"
```

Bot de Telegram:

```powershell
& ".\Iniciar bot.bat"
```

La computadora debe estar encendida y conectada a internet para que Telegram responda. Al volver a encenderla, ejecutá **Iniciar sistema.bat** de nuevo. El panel local abre en <http://127.0.0.1:8000>.

### Acceso desde celulares o computadoras en la misma Wi-Fi

1. Conectá la computadora que ejecuta el sistema y los celulares a la misma red Wi-Fi.
2. Iniciá **Iniciar sistema.bat**. La ventana indicará una dirección parecida a `http://192.168.1.25:8000`.
3. En cada celular o computadora, abrí esa dirección en el navegador e iniciá sesión con el usuario del rol correspondiente.
4. Si Windows pregunta por el Firewall, permití el acceso solo en redes privadas.

El enlace solo funciona mientras esta computadora esté encendida y el sistema siga abierto. No sirve desde otra red ni desde internet. Para presentar el sistema a personas que estén fuera de tu Wi-Fi, primero hay que alojarlo en un servidor HTTPS y ajustar las cuentas y contraseñas; no publiques el enlace local ni abras el puerto del router.

## Pedidos y pagos

El bot muestra el catálogo si el cliente escribe un saludo o cualquier mensaje libre, y también con `/start` y `/productos`. Para pedir, el cliente usa `/pedido`; para consultar el estado, `/estado NUMERO`. El despachante puede ver el importe de cambio cuando el cliente elige efectivo. La respuesta a texto libre es una bienvenida automática con el catálogo, no una conversación de inteligencia artificial para responder preguntas abiertas.

Para transferencia, el bot pide una foto o un PDF del comprobante. El administrador o despachante puede abrirlo en el panel y marcarlo verificado después de revisar el ingreso en la cuenta. El bot no puede confirmar por sí solo que una transferencia haya llegado: una imagen es solo un comprobante enviado. `DELY.DRINKS` es un alias de demostración, no una cuenta bancaria. Antes de aceptar transferencias reales, agregá `TRANSFER_ALIAS` con el alias real de la cuenta receptora en `.env`.

El bot informa el horario de atención de 10:00 a 13:30 y la dirección del comercio: Mitre 280, Resistencia, Chaco. Los envíos son únicamente al microcentro de Resistencia, con un costo fijo de $1.500. Se suma al total, queda guardado con el pedido y se muestra en los paneles y en el historial diario.

La aplicación todavía corre solo en esta computadora. Para compartir el panel por internet hay que publicarlo en un servidor con HTTPS y protección de acceso; no compartas el enlace local `127.0.0.1`.
