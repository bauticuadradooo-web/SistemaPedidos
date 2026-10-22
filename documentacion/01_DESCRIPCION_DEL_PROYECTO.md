# Dely Drinks — Descripción del proyecto

Fecha de elaboración: 21/10/2026. Fecha límite de entrega: 04/11/2026.

## Resumen y propuesta de valor
Dely Drinks es un sistema de gestión de pedidos de bebidas que conecta la compra por Telegram con la operación de un comercio mediante un panel web. Permite organizar catálogo, existencias, preparación, despacho, comprobantes y seguimiento de pedidos.

## Problema que resuelve
Cuando un comercio atiende pedidos con mensajes sueltos, el personal debe reconstruir productos, cantidades, dirección y pago. Esto dificulta conocer qué preparar, qué entregar y qué mercadería sigue disponible. El sistema centraliza esa información, registra cambios y separa responsabilidades mediante roles.

## Público objetivo
Pequeños comercios de bebidas con entrega a domicilio y un equipo que necesita coordinar administración, preparación y reparto. El cliente utiliza Telegram; el personal utiliza un navegador. La implementación actual está configurada para un comercio y una zona de entrega denominada microcentro de Resistencia, Chaco. No realiza geolocalización ni verifica automáticamente que una dirección pertenezca a esa zona.

## Objetivo general
Organizar el ciclo de un pedido desde su confirmación hasta la entrega o cancelación, manteniendo información persistente y existencias coherentes.

## Objetivos específicos
- Recibir productos, cantidades y datos de entrega desde un flujo guiado en Telegram.
- Revalidar existencias al confirmar y calcular el importe con envío.
- Distribuir tareas entre administrador, preparador y despachante.
- Registrar cambios, bajas de inventario e incidencias con motivo y autor.
- Consultar jornadas y ventas de pedidos entregados.
- Registrar la revisión humana de transferencias y los comprobantes de devoluciones.
- Crear respaldos de la base SQLite e informes de lectura.

## Presentación comercial
Con Dely Drinks, tu comercio puede organizar pedidos y entregas desde un mismo sistema. Tus clientes eligen por Telegram y tu equipo consulta qué preparar, qué despachar y en qué estado está cada compra. El control de existencias y el historial de operaciones ayudan a reducir errores y a trabajar con información compartida.

## Beneficios esperados y límites de la evidencia
Se espera reducir la transcripción manual y mejorar la coordinación. No se dispone de un estudio de tiempos, costos o ventas que permita afirmar porcentajes de mejora. La aplicación registra operaciones; no acredita pagos ni realiza transferencias bancarias.
