"""Bot de pedidos con long polling. Ejecutar con python -m app.telegram_bot."""
import os
import asyncio
from fastapi import HTTPException

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.database import SessionLocal
from app.models import Pedido, Producto, EventoPedido
from app.schemas import DetallePedidoCreate, PedidoCreate
from app.services.pedidos import COSTO_ENVIO_MICROCENTRO, crear_pedido
from app.services.cambios import cancelar_por_cliente
from app.services.telegram import enviar_evento
from app.services.devoluciones import guardar_alias_cliente, validar_alias

NOMBRE, DIRECCION, TELEFONO, PRODUCTOS, CANTIDAD, PAGO, MONTO_EFECTIVO, COMPROBANTE, CONFIRMAR = range(9)
ALIAS_TRANSFERENCIA = 9

INFO_COMERCIO = (
    "\n\n📍 Estamos en Mitre 280, Resistencia, Chaco."
    "\n🕙 Horario de atención: 10:00 a 13:30."
    "\n🛵 Envío solo al microcentro de Resistencia: $1.500."
)


def leer_catalogo():
    with SessionLocal() as db:
        return db.query(Producto).filter(Producto.stock > 0).order_by(Producto.nombre).all()


def precio_texto(precio):
    return f"{precio:,.0f}".replace(",", ".")


def alias_transferencia():
    return os.getenv("TRANSFER_ALIAS", "DELY.DRINKS")


def total_y_lineas(pedido):
    lineas = []
    total = 0
    with SessionLocal() as db:
        for detalle in pedido["detalles"]:
            producto = db.query(Producto).filter(Producto.id == detalle["producto_id"]).first()
            if not producto or producto.stock < detalle["cantidad"]:
                return None, None
            subtotal = producto.precio * detalle["cantidad"]
            lineas.append(f"• {producto.nombre} × {detalle['cantidad']} — ${precio_texto(subtotal)}")
            total += subtotal
    lineas.append(f"• Envío al microcentro — ${precio_texto(COSTO_ENVIO_MICROCENTRO)}")
    total += COSTO_ENVIO_MICROCENTRO
    return lineas, total


async def enviar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE, editar=False):
    pedido = context.user_data["pedido"]
    lineas, total = total_y_lineas(pedido)
    if lineas is None:
        mensaje = "Cambió el stock mientras armábamos el pedido. Iniciá uno nuevo con /pedido."
        if editar and update.callback_query:
            await update.callback_query.edit_message_text(mensaje)
        else:
            await update.effective_message.reply_text(mensaje)
        context.user_data.pop("pedido", None)
        return ConversationHandler.END

    if pedido.get("metodo_pago") == "Efectivo" and pedido.get("monto_efectivo", 0) < total:
        await update.effective_message.reply_text(
            f"El total cambió a ${precio_texto(total)}. Indicá con cuánto vas a pagar en efectivo."
        )
        return MONTO_EFECTIVO

    pedido["total_estimado"] = total
    texto = "Revisá tu pedido:\n\n" + "\n".join(lineas)
    texto += f"\n\nTotal: ${precio_texto(total)}\nEntrega: {pedido['direccion']}\nPago: {pedido['metodo_pago']}"
    if pedido["metodo_pago"] == "Efectivo":
        texto += f"\nPagás con: ${precio_texto(pedido['monto_efectivo'])}\nCambio para llevar: ${precio_texto(pedido['monto_efectivo'] - total)}"
    elif pedido["metodo_pago"] == "Transferencia":
        texto += f"\nAlias para transferencia: {alias_transferencia()}\nComprobante recibido; pendiente de revisión del comercio."

    teclado = InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirmar pedido", callback_data="confirmar")],
        [InlineKeyboardButton("Modificar pedido", callback_data="modificar")],
        [InlineKeyboardButton("Cancelar", callback_data="cancelar")],
    ])
    if editar and update.callback_query:
        await update.callback_query.edit_message_text(texto, reply_markup=teclado)
    else:
        await update.effective_message.reply_text(texto, reply_markup=teclado)
    return CONFIRMAR


def cantidad_en_pedido(pedido, producto_id):
    return next(
        (detalle["cantidad"] for detalle in pedido["detalles"] if detalle["producto_id"] == producto_id),
        0,
    )


def teclado_productos(pedido=None):
    productos = [
        producto for producto in leer_catalogo()
        if pedido is None
        or cantidad_en_pedido(pedido, producto.id) > 0
        or cantidad_en_pedido(pedido, producto.id) < producto.stock
    ]
    botones = []
    for producto in productos:
        cantidad = cantidad_en_pedido(pedido, producto.id) if pedido else 0
        etiqueta = f"{producto.nombre} · ${precio_texto(producto.precio)} · stock {producto.stock}"
        if cantidad:
            etiqueta += f" · en pedido {cantidad}"
        botones.append([InlineKeyboardButton(etiqueta, callback_data=f"producto:{producto.id}")])
        if cantidad:
            botones.append([
                InlineKeyboardButton("−", callback_data=f"carrito:menos:{producto.id}"),
                InlineKeyboardButton(f"{cantidad} en pedido", callback_data=f"producto:{producto.id}"),
                InlineKeyboardButton("+", callback_data=f"carrito:mas:{producto.id}"),
                InlineKeyboardButton("Quitar", callback_data=f"carrito:quitar:{producto.id}"),
            ])
    total_unidades = sum(detalle["cantidad"] for detalle in pedido["detalles"]) if pedido else 0
    botones.append([InlineKeyboardButton(f"Finalizar pedido ({total_unidades})", callback_data="finalizar")])
    return InlineKeyboardMarkup(botones), productos


def teclado_cantidad(cantidad, maximo, ya_agregado=False):
    botones = [
        [
            InlineKeyboardButton("−", callback_data="cantidad:menos"),
            InlineKeyboardButton(str(cantidad), callback_data="cantidad:actual"),
            InlineKeyboardButton("+", callback_data="cantidad:mas"),
        ],
        [InlineKeyboardButton("Guardar cantidad" if ya_agregado else f"Agregar {cantidad} al pedido", callback_data="cantidad:agregar")],
    ]
    if ya_agregado:
        botones.append([InlineKeyboardButton("Quitar producto del pedido", callback_data="cantidad:quitar")])
    botones.append(
        [InlineKeyboardButton("Volver al catálogo", callback_data="cantidad:volver")],
    )
    return InlineKeyboardMarkup(botones)


def cantidad_maxima_disponible(producto, pedido):
    return producto.stock


async def editar_catalogo(update, context):
    pedido = context.user_data["pedido"]
    keyboard, productos = teclado_productos(pedido)
    if not productos:
        if pedido["detalles"]:
            await update.callback_query.edit_message_text(
                "Agregaste todo el stock disponible. Podés finalizar el pedido.",
                reply_markup=keyboard,
            )
            return PRODUCTOS
        await update.callback_query.edit_message_text("No hay productos con stock disponible en este momento.")
        return ConversationHandler.END
    resumen = ""
    if pedido["detalles"]:
        with SessionLocal() as db:
            lineas = []
            for detalle in pedido["detalles"]:
                producto = db.query(Producto).filter(Producto.id == detalle["producto_id"]).first()
                if producto:
                    lineas.append(f"• {producto.nombre} × {detalle['cantidad']}")
        resumen = "\n\nTu pedido hasta ahora:\n" + "\n".join(lineas)
    await update.callback_query.edit_message_text(
        "Elegí un producto. Tocá + o − para indicar cuántos querés." + resumen
        + f"\n\nEnvío al microcentro: ${precio_texto(COSTO_ENVIO_MICROCENTRO)}.",
        reply_markup=keyboard,
    )
    return PRODUCTOS


def texto_catalogo(incluir_bienvenida=False):
    productos = leer_catalogo()
    if not productos:
        encabezado = "¡Hola! " if incluir_bienvenida else ""
        return encabezado + "Por el momento no hay productos disponibles. Volvé a consultar más tarde con /productos." + INFO_COMERCIO

    encabezado = "¡Hola! Este es el catálogo disponible:\n\n" if incluir_bienvenida else "Catálogo disponible:\n\n"
    lineas = [f"• {p.nombre} — ${precio_texto(p.precio)}" for p in productos]
    pie = "\n\nPara hacer un pedido, escribí /pedido.\nPara consultar el estado, escribí /estado seguido del número de pedido.\nPara cancelar un pedido pendiente: /cancelar_pedido NUMERO. Una vez en preparación ya no se puede cancelar."
    return encabezado + "\n".join(lineas) + pie + INFO_COMERCIO


def teclado_inicio_pedido():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Hacer un pedido", callback_data="iniciar_pedido")]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(texto_catalogo(incluir_bienvenida=True), reply_markup=teclado_inicio_pedido())


async def productos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(texto_catalogo(), reply_markup=teclado_inicio_pedido())


async def responder_mensaje_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ante un saludo o texto fuera del flujo, ofrece el catálogo sin comandos."""
    if context.user_data.get("pedido"):
        return
    catalogo = texto_catalogo().replace("Catálogo disponible:", "Este es el catálogo disponible:", 1)
    await update.effective_message.reply_text(
        f"¡Hola! Gracias por escribir a Dely Drinks.\n\n{catalogo}",
        reply_markup=teclado_inicio_pedido(),
    )


async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Para consultar un pedido, escribí /estado seguido del número. Ejemplo: /estado 12")
        return
    pedido_id = int(context.args[0])
    telegram_id = str(update.effective_user.id)
    with SessionLocal() as db:
        pedido = db.query(Pedido).filter(
            Pedido.id == pedido_id,
            Pedido.telegram_user_id == telegram_id,
        ).first()
        if not pedido:
            await update.message.reply_text("No encontré ese pedido asociado a tu cuenta de Telegram.")
            return
        estados = {"pendiente": "pendiente", "preparando": "en preparación", "listo_para_despacho": "listo para despacho", "en_camino": "en camino", "entregado": "entregado", "cancelado": "cancelado"}
        novedades = db.query(EventoPedido).filter(EventoPedido.pedido_id == pedido.id).order_by(EventoPedido.id.desc()).limit(3).all()
        texto = f"El pedido #{pedido.id} está {estados.get(pedido.estado, pedido.estado)}.\nTotal: ${precio_texto(pedido.total)}."
        for novedad in reversed(novedades):
            texto += "\n\n" + novedad.descripcion
        await update.message.reply_text(texto[:4000], reply_markup=boton_cancelacion(pedido.id) if pedido.estado == "pendiente" else None)


def boton_cancelacion(pedido_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar pedido pendiente", callback_data=f"anular:consultar:{pedido_id}")]])


async def cancelar_pedido_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        if len(context.args) != 1 or not context.args[0].isdigit():
            await update.effective_message.reply_text("Usá /cancelar_pedido NUMERO. Ejemplo: /cancelar_pedido 12")
            return
        pedido_id = int(context.args[0])
        with SessionLocal() as db:
            pedido = db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.telegram_user_id == str(update.effective_user.id)).first()
            if not pedido:
                await update.effective_message.reply_text("No encontré ese pedido asociado a tu cuenta de Telegram.")
                return
            if pedido.estado != "pendiente":
                await update.effective_message.reply_text("Solo podés cancelar un pedido pendiente. Una vez en preparación ya no se puede cancelar.")
                return
        await update.effective_message.reply_text(f"Pedido #{pedido_id}: tocá el botón para solicitar la cancelación.", reply_markup=boton_cancelacion(pedido_id))
        return
    with SessionLocal() as db:
        pedidos = db.query(Pedido).filter(Pedido.telegram_user_id == str(update.effective_user.id), Pedido.estado == "pendiente").order_by(Pedido.id.desc()).limit(10).all()
    if not pedidos:
        await update.effective_message.reply_text("No tenés pedidos pendientes que se puedan cancelar. Una vez en preparación ya no se puede cancelar.")
        return
    botones = [[InlineKeyboardButton(f"Cancelar pedido #{p.id}", callback_data=f"anular:consultar:{p.id}")] for p in pedidos]
    await update.effective_message.reply_text("Elegí el pedido pendiente que querés cancelar:", reply_markup=InlineKeyboardMarkup(botones))


async def cancelar_pedido_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, accion, id_texto = query.data.split(":")
    pedido_id = int(id_texto)
    if accion == "volver":
        await query.edit_message_text(f"No cancelamos el pedido #{pedido_id}. Consultá su estado con /estado {pedido_id}.")
        return
    if accion == "consultar":
        with SessionLocal() as db:
            pedido = db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.telegram_user_id == str(update.effective_user.id)).first()
            disponible = pedido and pedido.estado == "pendiente"
        if not disponible:
            await query.edit_message_text("El pedido no está disponible para cancelar. Solo se permite mientras está pendiente.")
            return
        await query.edit_message_text(f"¿Confirmás cancelar por completo el pedido #{pedido_id}? Si ya transferiste, tendrás que coordinar la devolución con el comercio.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Sí, cancelar", callback_data=f"anular:confirmar:{pedido_id}")],
            [InlineKeyboardButton("Conservar pedido", callback_data=f"anular:volver:{pedido_id}")],
        ]))
        return
    try:
        with SessionLocal() as db:
            evento_id = cancelar_por_cliente(db, pedido_id, str(update.effective_user.id))
    except HTTPException as error:
        await query.edit_message_text(str(error.detail))
        return
    with SessionLocal() as db:
        pedido_cancelado = db.get(Pedido, pedido_id)
        aviso = instrucciones_devolucion(pedido_cancelado)
    await query.edit_message_text(f"Pedido #{pedido_id} cancelado." + aviso)
    await asyncio.to_thread(enviar_evento, evento_id)


def instrucciones_devolucion(pedido):
    if pedido.metodo_pago != 'Transferencia':
        return ''
    if pedido.alias_cliente:
        return (f"\nInformaste como cuenta de origen: {pedido.alias_cliente}. El comercio debe verificarla contra el pago recibido y gestionar la devolución. Te enviaremos el comprobante por Telegram cuando lo carguen."
                f"\nSi necesitás corregirla: /alias_devolucion {pedido.id} TU_ALIAS")
    return (f"\nPara gestionar la devolución, enviá el alias o CBU/CVU de la misma cuenta desde la que pagaste: /alias_devolucion {pedido.id} TU_ALIAS. Cuando el comercio registre la devolución, recibirás el comprobante por Telegram.")


async def alias_devolucion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2 or not context.args[0].isdigit():
        await update.effective_message.reply_text('Usá /alias_devolucion NUMERO TU_ALIAS. Debe ser la misma cuenta desde la que transferiste.')
        return
    try:
        with SessionLocal() as db:
            guardar_alias_cliente(db, int(context.args[0]), str(update.effective_user.id), context.args[1])
    except HTTPException as error:
        await update.effective_message.reply_text(str(error.detail))
        return
    await update.effective_message.reply_text('Guardamos la cuenta que informaste. El comercio la verificará contra el pago recibido antes de devolver el dinero. Esto no realiza una transferencia automáticamente.')


async def iniciar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    if not leer_catalogo():
        await update.effective_message.reply_text("Todavía no hay productos disponibles para pedir. Volvé a consultar más tarde con /productos." + INFO_COMERCIO)
        return ConversationHandler.END
    context.user_data["pedido"] = {"detalles": []}
    await update.effective_message.reply_text("Vamos a armar tu pedido. ¿A nombre de quién lo registramos?" + INFO_COMERCIO)
    return NOMBRE


async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pedido"]["cliente"] = update.message.text.strip()[:120]
    await update.message.reply_text("¿A qué dirección lo llevamos?")
    return DIRECCION


async def recibir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pedido"]["direccion"] = update.message.text.strip()[:250]
    await update.message.reply_text("¿Cuál es tu teléfono de contacto?")
    return TELEFONO


async def recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pedido"]["telefono"] = update.message.text.strip()[:40]
    context.user_data["pedido"]["zona_entrega"] = "microcentro"
    return await mostrar_catalogo(update, context)


async def mostrar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard, productos = teclado_productos(context.user_data["pedido"])
    if not productos:
        await update.effective_message.reply_text("No hay productos con stock disponible en este momento. Probá más tarde con /pedido.")
        context.user_data.pop("pedido", None)
        return ConversationHandler.END
    await update.effective_message.reply_text(
        f"Elegí un producto. Podés sumar varios y después tocar ‘Finalizar pedido’.\nEnvío solo al microcentro de Resistencia: ${precio_texto(COSTO_ENVIO_MICROCENTRO)} (se suma al total):",
        reply_markup=keyboard,
    )
    return PRODUCTOS


async def elegir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("carrito:"):
        _, accion, id_texto = query.data.split(":", 2)
        producto_id = int(id_texto)
        pedido = context.user_data["pedido"]
        linea = next((d for d in pedido["detalles"] if d["producto_id"] == producto_id), None)
        producto = next((p for p in leer_catalogo() if p.id == producto_id), None)
        if not linea:
            return await editar_catalogo(update, context)
        if accion == "quitar":
            pedido["detalles"].remove(linea)
        elif accion == "menos":
            linea["cantidad"] -= 1
            if linea["cantidad"] <= 0:
                pedido["detalles"].remove(linea)
        elif accion == "mas" and producto and linea["cantidad"] < producto.stock:
            linea["cantidad"] += 1
        return await editar_catalogo(update, context)
    if query.data == "finalizar":
        if not context.user_data["pedido"]["detalles"]:
            await query.edit_message_text("Todavía no agregaste productos. Elegí al menos uno para continuar.", reply_markup=teclado_productos()[0])
            return PRODUCTOS
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Efectivo", callback_data="pago:Efectivo")],
            [InlineKeyboardButton("Transferencia", callback_data="pago:Transferencia")],
            [InlineKeyboardButton("Coordinar", callback_data="pago:Coordinar")],
            [InlineKeyboardButton("Volver al catálogo", callback_data="atras:productos")],
        ])
        await query.edit_message_text("¿Cómo preferís pagar?", reply_markup=keyboard)
        return PAGO

    producto_id = int(query.data.split(":", 1)[1])
    producto = next((p for p in leer_catalogo() if p.id == producto_id), None)
    if not producto or cantidad_maxima_disponible(producto, context.user_data["pedido"]) < 1:
        await query.edit_message_text("Ese producto ya no tiene stock disponible. Elegí otro:", reply_markup=teclado_productos(context.user_data["pedido"])[0])
        return PRODUCTOS
    context.user_data["producto_actual"] = producto_id
    cantidad_actual = cantidad_en_pedido(context.user_data["pedido"], producto_id)
    context.user_data["cantidad_actual"] = cantidad_actual or 1
    maximo = cantidad_maxima_disponible(producto, context.user_data["pedido"])
    await query.edit_message_text(
        f"{producto.nombre} — ${precio_texto(producto.precio)} cada uno\n"
        f"Elegí la cantidad total (máximo disponible: {maximo}):",
        reply_markup=teclado_cantidad(
            context.user_data["cantidad_actual"], maximo, ya_agregado=bool(cantidad_actual)
        ),
    )
    return CANTIDAD


async def ajustar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    producto_id = context.user_data.get("producto_actual")
    producto = next((p for p in leer_catalogo() if p.id == producto_id), None)
    pedido = context.user_data.get("pedido")
    if not producto or not pedido:
        context.user_data.pop("producto_actual", None)
        context.user_data.pop("cantidad_actual", None)
        await query.edit_message_text("El stock cambió. Iniciá el pedido nuevamente con /pedido.")
        return ConversationHandler.END

    maximo = cantidad_maxima_disponible(producto, pedido)
    if maximo < 1:
        await query.edit_message_text("Ya agregaste todo el stock disponible de este producto.", reply_markup=teclado_productos(pedido)[0])
        return PRODUCTOS

    accion = query.data.split(":", 1)[1]
    cantidad = context.user_data.get("cantidad_actual", 1)
    if accion == "menos":
        cantidad = max(1, cantidad - 1)
    elif accion == "mas":
        cantidad = min(maximo, cantidad + 1)
    elif accion == "actual":
        pass
    elif accion == "volver":
        context.user_data.pop("producto_actual", None)
        context.user_data.pop("cantidad_actual", None)
        return await editar_catalogo(update, context)
    elif accion == "agregar":
        linea = next((d for d in pedido["detalles"] if d["producto_id"] == producto_id), None)
        if linea:
            linea["cantidad"] = cantidad
        else:
            pedido["detalles"].append({"producto_id": producto_id, "cantidad": cantidad})
        context.user_data.pop("producto_actual", None)
        context.user_data.pop("cantidad_actual", None)
        return await editar_catalogo(update, context)
    elif accion == "quitar":
        pedido["detalles"] = [d for d in pedido["detalles"] if d["producto_id"] != producto_id]
        context.user_data.pop("producto_actual", None)
        context.user_data.pop("cantidad_actual", None)
        return await editar_catalogo(update, context)

    context.user_data["cantidad_actual"] = cantidad
    await query.edit_message_reply_markup(
        reply_markup=teclado_cantidad(
            cantidad, maximo, ya_agregado=cantidad_en_pedido(pedido, producto_id) > 0
        )
    )
    return CANTIDAD


async def elegir_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "atras:productos":
        return await editar_catalogo(update, context)
    pedido = context.user_data["pedido"]
    pedido["metodo_pago"] = query.data.split(":", 1)[1]
    lineas, total = total_y_lineas(pedido)
    if lineas is None:
        await query.edit_message_text("Cambió el stock mientras armábamos el pedido. Iniciá uno nuevo con /pedido.")
        context.user_data.pop("pedido", None)
        return ConversationHandler.END

    if pedido["metodo_pago"] == "Efectivo":
        pedido["total_estimado"] = total
        await query.edit_message_text(
            f"El total con envío es ${precio_texto(total)}. ¿Con cuánto vas a pagar? Escribí el monto en pesos, por ejemplo 25000."
        )
        return MONTO_EFECTIVO

    if pedido["metodo_pago"] == "Transferencia":
        await query.edit_message_text(
            f"Alias del comercio para pagar: {alias_transferencia()}\nEnvío al microcentro: ${precio_texto(COSTO_ENVIO_MICROCENTRO)}\nTotal con envío: ${precio_texto(total)}.\nAntes de enviar el comprobante, escribí el alias o CBU/CVU de TU cuenta, desde la que vas a transferir. Lo usamos si corresponde una devolución a esa misma cuenta."
        )
        return ALIAS_TRANSFERENCIA

    return await enviar_resumen(update, context, editar=True)


async def recibir_alias_transferencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        alias = validar_alias(update.effective_message.text)
    except HTTPException as error:
        await update.effective_message.reply_text(str(error.detail))
        return ALIAS_TRANSFERENCIA
    context.user_data['pedido']['alias_cliente'] = alias
    await update.effective_message.reply_text(f'Cuenta de origen informada: {alias}. Ahora enviá una foto o un PDF del comprobante del pago al comercio ({alias_transferencia()}).')
    return COMPROBANTE


async def recibir_monto_efectivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().replace("$", "").replace(" ", "").replace(".", "").replace(",", "")
    if not texto.isdigit():
        await update.message.reply_text("Escribí el monto en pesos usando solo números. Ejemplo: 25000.")
        return MONTO_EFECTIVO
    monto = int(texto)
    total = context.user_data["pedido"].get("total_estimado", 0)
    if monto < total:
        await update.message.reply_text(f"El monto debe cubrir el total de ${precio_texto(total)}. Indicá con cuánto vas a pagar.")
        return MONTO_EFECTIVO
    context.user_data["pedido"]["monto_efectivo"] = monto
    return await enviar_resumen(update, context)


async def recibir_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.effective_message
    if mensaje.photo:
        archivo = mensaje.photo[-1]
        file_id = archivo.file_id
        mime_type = "image/jpeg"
        nombre = "comprobante.jpg"
        size = archivo.file_size or 0
    elif mensaje.document:
        archivo = mensaje.document
        mime_type = archivo.mime_type or ""
        if mime_type not in {"application/pdf", "image/jpeg", "image/png"}:
            await mensaje.reply_text("Mandá el comprobante como foto o como archivo PDF, JPG o PNG.")
            return COMPROBANTE
        file_id = archivo.file_id
        nombre = (archivo.file_name or "comprobante").replace("\r", "").replace("\n", "")[:255]
        size = archivo.file_size or 0
    else:
        await mensaje.reply_text("Para seguir, enviá una foto o un archivo PDF del comprobante.")
        return COMPROBANTE

    if size > 20 * 1024 * 1024:
        await mensaje.reply_text("El comprobante debe pesar menos de 20 MB. Enviá una imagen más liviana o un PDF comprimido.")
        return COMPROBANTE

    pedido = context.user_data["pedido"]
    pedido["comprobante_file_id"] = file_id
    pedido["comprobante_mime_type"] = mime_type
    pedido["comprobante_nombre"] = nombre
    return await enviar_resumen(update, context)


async def confirmar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "modificar":
        return await editar_catalogo(update, context)
    if query.data == "cancelar":
        context.user_data.pop("pedido", None)
        await query.edit_message_text("Pedido cancelado. Cuando quieras, podés empezar de nuevo con /pedido.")
        return ConversationHandler.END
    datos = context.user_data.pop("pedido")
    datos.pop("total_estimado", None)
    datos["telegram_user_id"] = str(update.effective_user.id)
    datos["detalles"] = [DetallePedidoCreate(**d) for d in datos["detalles"]]
    try:
        with SessionLocal() as db:
            pedido = crear_pedido(db, PedidoCreate(**datos))
    except Exception:
        await query.edit_message_text("No pude registrar el pedido; puede haber cambiado el stock. Escribí /pedido para intentarlo otra vez.")
        return ConversationHandler.END
    await query.edit_message_text(f"¡Listo! Recibimos tu pedido #{pedido.id} por ${precio_texto(pedido.total)}. Te avisaremos cuando cambie su estado. También podés consultar con /estado {pedido.id}. Podés cancelarlo solo mientras esté pendiente; una vez en preparación no se puede.", reply_markup=boton_cancelacion(pedido.id))
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args or not context.user_data.get("pedido"):
        await cancelar_pedido_cmd(update, context)
        return
    context.user_data.pop("pedido", None)
    await update.effective_message.reply_text("Descarté el carrito sin confirmar. Los pedidos ya realizados no cambiaron. Para cancelar uno pendiente: /cancelar_pedido NUMERO.")
    return ConversationHandler.END


def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN. Copiá .env.example a .env y agregá allí el token de BotFather.")

    conversacion = ConversationHandler(
        entry_points=[CommandHandler("pedido", iniciar_pedido), CallbackQueryHandler(iniciar_pedido, pattern=r"^iniciar_pedido$")],
        states={
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre)],
            DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_direccion)],
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono)],
            PRODUCTOS: [CallbackQueryHandler(elegir_producto, pattern=r"^(producto:\d+|carrito:(menos|mas|quitar):\d+|finalizar)$")],
            CANTIDAD: [CallbackQueryHandler(ajustar_cantidad, pattern=r"^cantidad:(menos|mas|actual|agregar|volver)$")],
            PAGO: [CallbackQueryHandler(elegir_pago, pattern=r"^(pago:(Efectivo|Transferencia|Coordinar)|atras:productos)$")],
            MONTO_EFECTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto_efectivo)],
            ALIAS_TRANSFERENCIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_alias_transferencia)],
            COMPROBANTE: [MessageHandler(filters.PHOTO | filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), recibir_comprobante)],
            CONFIRMAR: [CallbackQueryHandler(confirmar_pedido, pattern=r"^(confirmar|modificar|cancelar)$")],
        },
        fallbacks=[CommandHandler("cancelar", cancelar), CommandHandler("pedido", iniciar_pedido)],
    )
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("productos", productos_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("cancelar_pedido", cancelar_pedido_cmd))
    app.add_handler(CommandHandler("alias_devolucion", alias_devolucion_cmd))
    app.add_handler(conversacion)
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(CallbackQueryHandler(cancelar_pedido_callback, pattern=r"^anular:(consultar|confirmar|volver):\d+$"))
    # Grupo posterior: cubre mensajes libres cuando no hay pedido en curso.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensaje_libre), group=1)
    app.run_polling()


if __name__ == "__main__":
    main()
