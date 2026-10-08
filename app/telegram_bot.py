"""Bot de pedidos con long polling. Ejecutar con python -m app.telegram_bot."""
import os

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
from app.models import Pedido, Producto
from app.schemas import DetallePedidoCreate, PedidoCreate
from app.services.pedidos import COSTO_ENVIO_MICROCENTRO, crear_pedido

NOMBRE, DIRECCION, TELEFONO, PRODUCTOS, CANTIDAD, PAGO, MONTO_EFECTIVO, COMPROBANTE, CONFIRMAR = range(9)

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
        [InlineKeyboardButton("Cancelar", callback_data="cancelar")],
    ])
    if editar and update.callback_query:
        await update.callback_query.edit_message_text(texto, reply_markup=teclado)
    else:
        await update.effective_message.reply_text(texto, reply_markup=teclado)
    return CONFIRMAR


def teclado_productos():
    productos = leer_catalogo()
    botones = [[InlineKeyboardButton(f"{p.nombre} · ${precio_texto(p.precio)} · stock {p.stock}", callback_data=f"producto:{p.id}")] for p in productos]
    botones.append([InlineKeyboardButton("Finalizar pedido", callback_data="finalizar")])
    return InlineKeyboardMarkup(botones), productos


def texto_catalogo(incluir_bienvenida=False):
    productos = leer_catalogo()
    if not productos:
        encabezado = "¡Hola! " if incluir_bienvenida else ""
        return encabezado + "Por el momento no hay productos disponibles. Volvé a consultar más tarde con /productos." + INFO_COMERCIO

    encabezado = "¡Hola! Este es el catálogo disponible:\n\n" if incluir_bienvenida else "Catálogo disponible:\n\n"
    lineas = [f"• {p.nombre} — ${precio_texto(p.precio)}" for p in productos]
    pie = "\n\nPara hacer un pedido, escribí /pedido.\nPara consultar el estado, escribí /estado seguido del número de pedido."
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
        await update.message.reply_text(f"El pedido #{pedido.id} está {estados.get(pedido.estado, pedido.estado)}.")


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
    keyboard, productos = teclado_productos()
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
    if query.data == "finalizar":
        if not context.user_data["pedido"]["detalles"]:
            await query.edit_message_text("Todavía no agregaste productos. Elegí al menos uno para continuar.", reply_markup=teclado_productos()[0])
            return PRODUCTOS
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Efectivo", callback_data="pago:Efectivo")],
            [InlineKeyboardButton("Transferencia", callback_data="pago:Transferencia")],
            [InlineKeyboardButton("Coordinar", callback_data="pago:Coordinar")],
        ])
        await query.edit_message_text("¿Cómo preferís pagar?", reply_markup=keyboard)
        return PAGO

    producto_id = int(query.data.split(":", 1)[1])
    producto = next((p for p in leer_catalogo() if p.id == producto_id), None)
    if not producto:
        await query.edit_message_text("Ese producto ya no tiene stock. Elegí otro:", reply_markup=teclado_productos()[0])
        return PRODUCTOS
    context.user_data["producto_actual"] = producto_id
    await query.edit_message_text(f"¿Cuántas unidades de {producto.nombre} querés? (stock actual: {producto.stock})")
    return CANTIDAD


async def recibir_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit() or int(texto) < 1:
        await update.message.reply_text("Indicá una cantidad entera mayor a cero.")
        return CANTIDAD
    producto_id = context.user_data["producto_actual"]
    cantidad = int(texto)
    pedido = context.user_data["pedido"]
    linea = next((d for d in pedido["detalles"] if d["producto_id"] == producto_id), None)
    acumulado = cantidad + (linea["cantidad"] if linea else 0)
    producto = next((p for p in leer_catalogo() if p.id == producto_id), None)
    if not producto or acumulado > producto.stock:
        await update.message.reply_text("No alcanza el stock para esa cantidad. Probá con menos unidades.")
        return CANTIDAD
    if linea:
        linea["cantidad"] = acumulado
    else:
        pedido["detalles"].append({"producto_id": producto_id, "cantidad": cantidad})
    return await mostrar_catalogo(update, context)


async def elegir_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
            f"Alias para transferencia: {alias_transferencia()}\nEnvío al microcentro: ${precio_texto(COSTO_ENVIO_MICROCENTRO)}\nTotal con envío: ${precio_texto(total)}. Enviá una foto o un PDF del comprobante para continuar."
        )
        return COMPROBANTE

    return await enviar_resumen(update, context, editar=True)


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
    await query.edit_message_text(f"¡Listo! Recibimos tu pedido #{pedido.id} por ${precio_texto(pedido.total)}. Te avisaremos cuando cambie su estado. También podés consultar con /estado {pedido.id}.")
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pedido", None)
    await update.effective_message.reply_text("Listo, cancelé el pedido. Para volver a empezar, escribí /pedido.")
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
            PRODUCTOS: [CallbackQueryHandler(elegir_producto, pattern=r"^(producto:\d+|finalizar)$")],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cantidad)],
            PAGO: [CallbackQueryHandler(elegir_pago, pattern=r"^pago:(Efectivo|Transferencia|Coordinar)$")],
            MONTO_EFECTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto_efectivo)],
            COMPROBANTE: [MessageHandler(filters.PHOTO | filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), recibir_comprobante)],
            CONFIRMAR: [CallbackQueryHandler(confirmar_pedido, pattern=r"^(confirmar|cancelar)$")],
        },
        fallbacks=[CommandHandler("cancelar", cancelar), CommandHandler("pedido", iniciar_pedido)],
    )
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("productos", productos_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(conversacion)
    # Grupo posterior: cubre mensajes libres cuando no hay pedido en curso.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensaje_libre), group=1)
    app.run_polling()


if __name__ == "__main__":
    main()
