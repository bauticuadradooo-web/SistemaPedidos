# Bitácora del desarrollador

## Criterio de registro
Se reconstruyen incidencias a partir de documentación y código disponibles. Cuando no existe una fecha comprobable, se indica expresamente. Las pruebas aportan evidencia técnica de ciertos casos, pero no prueban cuándo ocurrió una incidencia real. No hay evidencia de conflictos entre integrantes ni se inventan reuniones, responsables o acuerdos.

| ID / fecha del hecho | Dificultad | Solución documentada o implementada | Evidencia y alcance |
| --- | --- | --- | --- |
| B01 / sin fecha comprobable | Dos procesos consultando el mismo bot generan conflicto getUpdates. | Iniciador para reiniciar una sola instancia del módulo. | README.actualizado.md y herramientas previas; no se reprodujo contra Telegram real. |
| B02 / 19/10/2026 según registro previo | El DNS del router no resolvía api.trycloudflare.com. | El registro indica uso de DNS públicos y comprobaciones del túnel antes de anunciar URL. | README.actualizado.md, sección de diagnóstico; no se cambiaron ajustes de red en esta tarea. |
| B03 / sin fecha comprobable | Cancelaciones repetidas/concurrentes podían afectar coherencia del stock. | Control de escritura y validación del estado antes de reponer. | services/cambios.py y test_cancelacion_concurrente_no_duplica_stock. |
| B04 / sin fecha comprobable | Una baja parcial por rotura no debe descontar dos veces una unidad ya reservada. | Diferenciar pérdida de unidad y reposición vendible. | test_parcial_perdida_sin_doble_descuento y test_parcial_reposicion_y_linea_completa. |
| B05 / sin fecha comprobable | Reintentar un comprobante de devolución podía duplicar registro o envío simultáneo. | Unicidad por pedido, reutilización del registro y control de envío en curso. | models.DevolucionPedido y pruebas de reintento/concurrencia. |
| B06 / sin fecha comprobable | Bases antiguas no tenían ciertas columnas nuevas. | Comprobar columnas y aplicar ALTER TABLE sin eliminar pedidos. | main.py y test_migracion_agrega_alias_sin_perder_pedidos; no equivale a migraciones completas. |
| B07 / 21/10/2026, relevamiento | La copia de presentación no tenía requirements.txt ni configuración de ejemplo, aunque su manual los mencionaba. | Preparar paquete nuevo con inventario exacto observado y .env.example sin secretos. | herramientas/VERSIONES.json y raíz del paquete. No se modificó la copia sincronizada. |
| B08 / 21/10/2026, relevamiento | Se declaraba soporte PostgreSQL, pero psycopg no estaba instalado en el entorno inspeccionado. | Delimitar entrega validada en SQLite y registrar PostgreSQL como opcional no probado. | Dependencias originales e inventario instalado; no se inventa versión del servidor PostgreSQL. |

## Nuevas entradas
Para futuras incidencias registrar: fecha real, autor, contexto, comportamiento esperado y observado, pasos para reproducir, impacto, causa confirmada o hipótesis, solución, evidencia de verificación y estado. Añadir coordinación del equipo únicamente cuando los participantes puedan confirmar el hecho.
