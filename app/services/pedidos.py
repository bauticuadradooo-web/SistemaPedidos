from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import DetallePedido, Pedido, Producto
from app.schemas import PedidoCreate
from app.services.jornadas import jornada_actual
from app.services.cambios import iniciar_escritura

COSTO_ENVIO_MICROCENTRO = 1500


def crear_pedido(db: Session, datos: PedidoCreate) -> Pedido:
    iniciar_escritura(db)
    cantidades = {}
    for detalle in datos.detalles:
        cantidades[detalle.producto_id] = cantidades.get(detalle.producto_id, 0) + detalle.cantidad

    productos = {}
    total = 0
    for producto_id, cantidad in sorted(cantidades.items()):
        producto = db.query(Producto).filter(Producto.id == producto_id).with_for_update().first()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
        if producto.stock < cantidad:
            raise HTTPException(status_code=400, detail=f"No hay suficiente stock de {producto.nombre}")
        productos[producto_id] = producto
        total += producto.precio * cantidad

    zona_entrega = "microcentro"
    costo_envio = COSTO_ENVIO_MICROCENTRO
    total += costo_envio

    if datos.metodo_pago == "Efectivo" and datos.monto_efectivo is not None and datos.monto_efectivo < total:
        raise HTTPException(status_code=400, detail="El monto en efectivo no cubre el total del pedido")

    jornada = jornada_actual(db)
    pedido = Pedido(
        jornada_id=jornada.id,
        cliente=datos.cliente,
        direccion=datos.direccion,
        telefono=datos.telefono,
        metodo_pago=datos.metodo_pago,
        zona_entrega=zona_entrega,
        costo_envio=costo_envio,
        monto_efectivo=datos.monto_efectivo,
        comprobante_file_id=datos.comprobante_file_id,
        comprobante_mime_type=datos.comprobante_mime_type,
        comprobante_nombre=datos.comprobante_nombre,
        pago_verificado=(datos.metodo_pago != "Transferencia"),
        telegram_user_id=datos.telegram_user_id,
        alias_cliente=datos.alias_cliente,
        total=total,
    )
    db.add(pedido)
    db.flush()

    for detalle in datos.detalles:
        producto = productos[detalle.producto_id]
        db.add(DetallePedido(
            pedido_id=pedido.id,
            producto_id=producto.id,
            cantidad=detalle.cantidad,
            precio=producto.precio,
        ))
    for producto_id, cantidad in cantidades.items():
        productos[producto_id].stock -= cantidad

    db.commit()
    db.refresh(pedido)
    return pedido
