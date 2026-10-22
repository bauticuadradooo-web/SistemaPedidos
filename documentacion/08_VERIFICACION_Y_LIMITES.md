# Verificación de la entrega

Fecha documental: 21/10/2026. Python utilizado: 3.14.4; SQLite: 3.50.4.

Se ejecutó `python -m unittest discover -s tests -t . -v` sobre el código copiado en el paquete académico con el intérprete del entorno original. Código de salida: 0. La salida completa está en RESULTADO_PRUEBAS.txt. Se emplean bases temporales y envíos simulados; no se opera con datos del comercio.

La suite cubre cambios parciales, permisos, bajas, cancelación del propietario, concurrencia, reintentos, devoluciones y migración de una columna. No demuestra el funcionamiento del token real, acceso público, acreditación bancaria ni rendimiento bajo carga. No se ejecutó una instalación nueva descargando dependencias ni un recorrido manual completo de interfaz durante esta preparación. La copia se coteja por SHA-256 con el código de referencia en MANIFIESTO_CODIGO.json.

Para aceptación manual: configurar usuarios ficticios, cargar un producto con stock 10, pedir 3, comprobar stock 7, preparar/despachar/entregar y comprobar ventas. Crear otro pedido pendiente, cancelarlo y comprobar reposición una sola vez. Revisar restricciones por rol y cierre de jornada. Registrar resultado, fecha y responsable al ejecutarlo; no se marca como realizado anticipadamente.

El repositorio GitHub se verificó como público mediante su API. El historial de la rama main identifica el commit de esta entrega. La identificación académica está en DATOS_DE_LA_ENTREGA.md. El commit de entrega puede consultarse en el historial del repositorio.

Resultado: 24 pruebas ejecutadas en 14,591 segundos, todas aprobadas. Se observaron advertencias de obsolescencia por datetime.utcnow() y por el cliente de pruebas de Starlette/httpx. No son fallos de la suite; deben considerarse al actualizar versiones. La primera ejecución dentro del sandbox se detuvo al crear un socket local de asyncio; la suite concluyó al ejecutarse fuera de esa restricción, sin modificar el código.

Resultado: 24 pruebas ejecutadas en 14,591 segundos, todas aprobadas. Se observaron advertencias de obsolescencia por datetime.utcnow() y por el cliente de pruebas de Starlette/httpx. No son fallos de la suite; deben considerarse al actualizar versiones. La primera ejecución dentro del sandbox se detuvo al crear un socket local de asyncio; la suite concluyó al ejecutarse fuera de esa restricción, sin modificar el código.
