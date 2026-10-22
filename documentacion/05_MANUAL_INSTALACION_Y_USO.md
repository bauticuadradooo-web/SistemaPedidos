# Instalación, operación y mantenimiento

## Instalación de la copia académica (PowerShell)
Usar Python 3.14.4 como versión de referencia. Abrir PowerShell en la raíz DelyDrinks_Entrega, donde están app/ y requirements.txt.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
New-Item -ItemType Directory -Force database | Out-Null
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Si .env ya existe, conservarlo y editarlo en lugar de reemplazarlo. El archivo requirements.txt de esta entrega fija todas las distribuciones observadas en el entorno local, excepto pip, que se registra como herramienta. Es una referencia para Windows y Python 3.14; no constituye una certificación para otros sistemas. No se requieren psycopg ni PostgreSQL para usar SQLite.

Abrir http://127.0.0.1:8000. En el primer inicio crear tres nombres distintos para administrador, preparador y despachante, con contraseñas de al menos 10 caracteres. No hay recuperación de contraseña desde la interfaz. Cargar productos ficticios con precio positivo y existencias suficientes.

## Configuración
TELEGRAM_BOT_TOKEN: token del bot propio creado en BotFather. TRANSFER_ALIAS: cuenta receptora real si se operan transferencias; para la evaluación usar datos ficticios y no transferir dinero. PANEL_COOKIE_SECURE=false para HTTP local; true para un acceso exclusivamente HTTPS. DATABASE_URL=sqlite:///./database/pedidos_comercio.db. Nunca publicar .env ni credenciales.

## Iniciar el bot
Con las tablas ya inicializadas por el panel, abrir otra terminal en la misma raíz:

```powershell
.\.venv\Scripts\python.exe -m app.telegram_bot
```

Se necesita internet y token válido. Mantener una sola instancia por token. El panel puede revisarse localmente sin iniciar Telegram. Usar las contraseñas creadas, no las ficticias de las pruebas.

## Operación diaria
1. Administrador revisa productos, precios y stock.
2. Cliente abre su bot y usa /start o /pedido; completa datos, carrito y forma de pago.
3. Al confirmar, el sistema revisa stock y guarda el pedido.
4. Preparador toma el pedido, prepara y lo deja listo.
5. Despachante revisa entrega y pago, marca en camino y entregado.
6. Administrador revisa ventas e historial y cierra jornada sin pedidos en curso.

El cliente consulta con /estado NUMERO. La cancelación del cliente exige propiedad del pedido y estado pendiente. Para pérdidas, reposiciones o incidencias, registrar un motivo concreto. Los comprobantes deben revisarse contra la cuenta bancaria; el sistema no confirma acreditaciones. Para devolución, realizar el reintegro fuera de la aplicación y registrar su comprobante real solo en una operación autorizada.

## Respaldo y restauración
Crear respaldo desde el panel y conservar .sqlite3 junto con el informe .html de database/backups. El HTML sirve para consulta y no sustituye la base. Para restaurar SQLite: detener bot y panel, conservar copia del archivo actual, verificar que la copia elegida corresponde a la instalación, reemplazar manualmente database/pedidos_comercio.db por una copia válida y reiniciar. Revisar integridad y pedidos antes de retomar operaciones. No practicar sobre información real durante la evaluación.

## Diagnóstico
- Error getUpdates/Conflict: detener instancias duplicadas del mismo bot y dejar una.
- No abre el panel: revisar terminal, puerto y directorio de ejecución.
- Falta módulo: comprobar que se usa el Python de .venv y que se instalaron dependencias.
- No envía Telegram: comprobar token/conexión de forma privada y revisar evento pendiente antes de reintentar.
- Túnel inaccesible: comprobar PC, procesos, DNS y enlace vigente. No se garantiza acceso desde todas las redes.

## Acceso opcional por Cloudflare
La herramienta observada es cloudflared 2026.10.0. Un túnel rápido genera una URL temporal y requiere que la PC siga encendida. El paquete incluye el script previo en Compartir-panel.ps1 como referencia; revisar sus requisitos antes de usarlo. No se requiere para evaluar la aplicación local. No representa alojamiento permanente.

## Ejecutar las pruebas
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```
Las pruebas crean una base temporal y simulan envíos. El informe adjunto documenta lo ejecutado durante esta preparación; el evaluador puede repetirlo.
