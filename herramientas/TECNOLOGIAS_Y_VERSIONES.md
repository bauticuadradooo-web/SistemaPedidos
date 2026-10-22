# Herramientas, tecnologías y versiones

Relevamiento del entorno virtual original, 21/10/2026. Se documentan las versiones realmente instaladas, sin confundirlas con los rangos del archivo original.

| Tecnología | Versión | Uso / verificación |
| --- | --- | --- |
| Python | 3.14.4 | Runtime, consultado en sys.version. |
| SQLite | 3.50.4 | Motor incorporado al Python inspeccionado, sqlite3.sqlite_version. |
| Git | 2.56.0.windows.2 | Control de versiones, git --version. |
| cloudflared | 2026.10.0 | Túnel opcional, cloudflared --version. |
| HTML | HTML5, doctype html | Estructura de las pantallas; no es una dependencia con versión de paquete. |
| CSS | Sin versión única fijada | Estilos incluidos en HTML; no hay compilador CSS declarado. |
| JavaScript | Sin edición ECMAScript fijada | Lógica del navegador; no hay Node.js ni framework frontend declarado. |
| SQL | Dialecto SQLite 3.50.4 | Consultas y esquema; PostgreSQL opcional sin versión verificada. |
| PowerShell / BAT | Versión objetivo no fijada | Scripts de Windows; no atribuir la versión del equipo de documentación a la PC original. |
| Telegram Bot API | Versión remota no fijada en el proyecto | Servicio externo; la versión del SDK se lista por separado. |
| GitHub | Servicio alojado sin versión local | Alojamiento del repositorio. |
| Windows / navegador / editor | Versión exacta no documentada | Windows observado; VS Code mencionado en manual anterior, versión no comprobada. |

## Todas las distribuciones Python instaladas

| Distribución | Versión exacta | Función / clasificación |
| --- | --- | --- |
| annotated-doc | 0.0.5 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| annotated-types | 0.8.0 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| anyio | 4.15.1 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| certifi | 2026.7.22 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| click | 8.5.0 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| fastapi | 0.141.1 | API HTTP y validación de rutas |
| h11 | 0.16.0 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| httpcore | 1.0.9 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| httptools | 0.8.0 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| httpx | 0.28.1 | HTTP saliente y pruebas |
| idna | 3.20 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| Jinja2 | 3.1.6 | Instalada; las pantallas actuales se sirven con FileResponse |
| MarkupSafe | 3.0.3 | Dependencia instalada de Jinja2 |
| pip | 26.0.1 | Instalador de paquetes |
| pydantic | 2.13.5 | Validación de datos |
| pydantic_core | 2.46.5 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| python-dotenv | 1.2.3 | Carga de configuración .env |
| python-telegram-bot | 22.8 | Conversación del bot |
| PyYAML | 6.0.3 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| SQLAlchemy | 2.1.1 | Mapeo y operaciones de base de datos |
| starlette | 1.7.0 | Infraestructura web de FastAPI |
| typing-inspection | 0.4.4 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| typing_extensions | 4.16.0 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| uvicorn | 0.54.0 | Servidor ASGI |
| watchfiles | 1.3.0 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |
| websockets | 17.2 | Dependencia de infraestructura o del entorno; instalada, no implica importación directa por la aplicación. |

## Dependencias directas y opcionales
Importaciones externas directas: FastAPI, SQLAlchemy, Pydantic, python-dotenv, python-telegram-bot y httpx. Uvicorn ejecuta el servidor. httpx se utiliza directamente aunque el requirements original lo obtiene transitivamente. psycopg[binary]>=3.2,<4.0 aparece en requirements original para PostgreSQL, pero no está instalado; no se fija una versión no comprobada. Jinja2 está instalada, pero las pantallas actuales no usan un motor de plantillas Jinja2.

## Biblioteca estándar
Los módulos estándar pertenecen a Python 3.14.4 y no se instalan con pip. El inventario automático de importaciones aparece en IMPORTACIONES.md. Incluye módulos como asyncio, sqlite3, hashlib, secrets, decimal, pathlib, datetime, json y unittest.

## Reproducción y actualización
requirements-entorno-observado.txt fija todas las distribuciones observadas excepto pip. requirements-original.txt conserva los rangos anteriores para comparación. Una instalación limpia debe verificarse antes de afirmar reproducibilidad total. Actualizar librerías requiere repetir pruebas; este inventario no pretende representar las versiones más recientes disponibles.
