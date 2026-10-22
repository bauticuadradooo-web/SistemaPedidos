"""Cambios de pedidos e inventario serializados con registro del motivo."""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text

from app.models import DetallePedido, EventoPedido, Jornada, MovimientoStock, Pedido, Producto


def iniciar_escritura(db):
    # SQLite no implementa FOR UPDATE. Reservar la escritura antes de leer evita
    # que preparar/cancelar o dos descuentos consuman las mismas existencias.
    if db.bind.dialect.name == "sqlite" and not db.in_transaction():
        db.execute(text("BEGIN IMMEDIATE"))


def pedido_editable(db, pedido_id):
    iniciar_escritura(db)
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).with_for_update().first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    jornada = db.get(Jornada, pedido.jornada_id) if pedido.jornada_id else None
    if jornada and jornada.cerrada_en is not None:
        raise HTTPException(409, "Ese pedido pertenece a un día finalizado")
    return pedido


def motivo_valido(motivo):
    motivo = motivo.strip()
    if not 3 <= len(motivo) <= 1000:
        raise HTTPException(422, "Explicá el motivo con entre 3 y 1000 caracteres")
    return motivo


def evento(db, pedido, tipo, descripcion, autor):
    registro = EventoPedido(pedido_id=pedido.id, tipo=tipo, descripcion=descripcion, autor=autor)
    db.add(registro)
    db.flush()
    return registro


def reponer_detalles(db, pedido, autor, motivo):
    # Orden fijo de bloqueo de productos, compartido con la creación de pedidos.
    for detalle in sorted(pedido.detalles, key=lambda d: (d.producto_id, d.id)):
        producto = db.query(Producto).filter(Producto.id == detalle.producto_id).with_for_update().first()
        if producto and detalle.cantidad:
            producto.stock += detalle.cantidad
            db.add(MovimientoStock(producto_id=producto.id, pedido_id=pedido.id,
                                   delta=detalle.cantidad, motivo=motivo, autor=autor))


def cancelar_por_cliente(db, pedido_id, telegram_id):
    pedido = pedido_editable(db, pedido_id)
    if pedido.telegram_user_id != str(telegram_id):
        raise HTTPException(404, "No encontré ese pedido asociado a tu cuenta de Telegram")
    if pedido.estado != "pendiente":
        raise HTTPException(409, "Solo podés cancelar mientras el pedido está pendiente. Una vez en preparación ya no se puede cancelar.")
    reponer_detalles(db, pedido, "cliente Telegram", "Cancelación del cliente mientras estaba pendiente")
    pedido.estado = "cancelado"
    texto = "Cancelaste tu pedido. Los productos volvieron al stock."
    if pedido.metodo_pago == 'Transferencia':
        texto += (f" El comercio gestionará la devolución a la cuenta de origen que informaste ({pedido.alias_cliente}) y te enviará el comprobante por Telegram." if pedido.alias_cliente else
                  f" Para gestionar la devolución a la misma cuenta desde la que pagaste, enviá /alias_devolucion {pedido.id} TU_ALIAS. Te enviaremos el comprobante cuando el comercio registre la devolución.")
    registro = evento(db, pedido, "cancelacion_cliente", texto, "cliente Telegram")
    db.commit()
    return registro.id


def cancelar_parcial(db, pedido_id, detalle_id, cantidad, motivo, reponer_stock, autor):
    motivo = motivo_valido(motivo)
    pedido = pedido_editable(db, pedido_id)
    if pedido.estado not in {"pendiente", "preparando", "listo_para_despacho"}:
        raise HTTPException(409, "Solo se pueden quitar productos antes de salir a reparto")
    detalle = db.query(DetallePedido).filter(DetallePedido.id == detalle_id, DetallePedido.pedido_id == pedido.id).first()
    if not detalle or cantidad < 1 or cantidad > detalle.cantidad:
        raise HTTPException(422, "La cantidad supera lo incluido en ese producto del pedido")
    if sum(d.cantidad for d in pedido.detalles) <= cantidad:
        raise HTTPException(409, "La cancelación parcial debe dejar al menos un producto. Para quitar todo, usá la cancelación completa.")
    producto = db.query(Producto).filter(Producto.id == detalle.producto_id).with_for_update().first()
    nombre = producto.nombre if producto else "Producto eliminado"
    if reponer_stock and producto:
        producto.stock += cantidad
    # El stock del pedido ya se descontó al crearlo. Si se dañó o no existe,
    # quitarlo no vuelve a descontar el disponible ni devuelve unidades ficticias.
    db.add(MovimientoStock(producto_id=detalle.producto_id, pedido_id=pedido.id,
                           delta=cantidad if reponer_stock and producto else 0,
                           motivo=f"Se quitaron {cantidad} de {nombre}. {'Vuelven al stock' if reponer_stock else 'No se reponen (faltante o pérdida)'}. {motivo}", autor=autor))
    descuento = Decimal(str(detalle.precio)) * cantidad
    detalle.cantidad -= cantidad
    if detalle.cantidad == 0:
        db.delete(detalle)
    pedido.total = float((Decimal(str(pedido.total)) - descuento).quantize(Decimal('0.01')))
    texto = f"Quitamos {cantidad} × {nombre} de tu pedido. Motivo: {motivo}\nNuevo total con envío: ${pedido.total:,.2f}. El resto del pedido sigue en curso."
    if pedido.metodo_pago == "Transferencia":
        texto += f"\nImporte a reintegrar si ya transferiste el total anterior: ${descuento:,.2f}. El comercio debe coordinar la devolución; no se realiza automáticamente."
    registro = evento(db, pedido, "cancelacion_parcial", texto, autor)
    db.commit()
    return registro.id
