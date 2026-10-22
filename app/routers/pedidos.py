import json
import os
from urllib.parse import quote, urlencode
from urllib.request import urlopen

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.auth import exigir_roles
from app.database import SessionLocal
from app.models import Jornada, Pedido, EventoPedido
from app.schemas import PedidoCreate
from app.services.jornadas import jornada_actual
from app.services.pedidos import crear_pedido as guardar_pedido
from app.services.telegram import notificar_estado, notificar_pago_verificado
from app.services.telegram import enviar_evento
from app.services.cambios import cancelar_parcial, evento, motivo_valido, pedido_editable, reponer_detalles

router = APIRouter()


class CancelacionParcial(BaseModel):
    detalle_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    motivo: str = Field(min_length=3, max_length=1000)
    reponer_stock: bool


class IncidenciaDelivery(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)


def eventos_a_dict(pedido):
    from sqlalchemy.orm import object_session
    db = object_session(pedido)
    registros = db.query(EventoPedido).filter(EventoPedido.pedido_id == pedido.id).order_by(EventoPedido.id).all()
    return [{"id": e.id, "tipo": e.tipo, "descripcion": e.descripcion,
             "autor": e.autor, "fecha": e.creado_en.isoformat() + "Z", "notificado": e.notificado,
             "telegram_disponible": bool(pedido.telegram_user_id)} for e in registros]


def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/pedidos")
def crear_pedido(
    pedido: PedidoCreate,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    return guardar_pedido(db, pedido)


def pedido_a_dict(pedido: Pedido, rol: str):
    detalles = [
        {
            "detalle_id": detalle.id,
            "producto_id": detalle.producto_id,
            "producto": detalle.producto.nombre if detalle.producto else "Producto eliminado",
            "cantidad": detalle.cantidad,
            "precio_unitario": detalle.precio,
            "subtotal": detalle.precio * detalle.cantidad,
        }
        for detalle in pedido.detalles
    ]
    if rol == "preparador":
        articulos = [{"detalle_id": d["detalle_id"], "producto_id": d["producto_id"], "producto": d["producto"], "cantidad": d["cantidad"]} for d in detalles]
        # Los importes y datos personales siguen reservados a administración/despacho.
        eventos = eventos_a_dict(pedido)
        for e in eventos:
            e["descripcion"] = e["descripcion"].split("\nNuevo total")[0]
        return {"id": pedido.id, "estado": pedido.estado, "detalles": articulos, "eventos": eventos}

    return {
        "id": pedido.id,
        "cliente": pedido.cliente,
        "direccion": pedido.direccion,
        "telefono": pedido.telefono,
        "metodo_pago": pedido.metodo_pago,
        "zona_entrega": pedido.zona_entrega,
        "costo_envio": pedido.costo_envio or 0,
        "subtotal_productos": pedido.total - (pedido.costo_envio or 0),
        "monto_efectivo": pedido.monto_efectivo,
        "cambio": max(0, pedido.monto_efectivo - pedido.total) if pedido.monto_efectivo is not None else None,
        "comprobante_disponible": bool(pedido.comprobante_file_id),
        "pago_verificado": bool(pedido.pago_verificado),
        "total": pedido.total,
        "estado": pedido.estado,
        "detalles": detalles,
        "eventos": eventos_a_dict(pedido),
    }


@router.get("/pedidos/todos")
def listar_pedidos(
    db: Session = Depends(obtener_db),
    usuario=Depends(exigir_roles("administrador", "preparador", "despachante")),
):
    jornada = jornada_actual(db)
    pedidos = db.query(Pedido).filter(Pedido.jornada_id == jornada.id).order_by(Pedido.id).all()
    if usuario.rol == "preparador":
        pedidos = [pedido for pedido in pedidos if pedido.estado in {"pendiente", "preparando"}]
    elif usuario.rol == "despachante":
        pedidos = [pedido for pedido in pedidos if pedido.estado in {"listo_para_despacho", "en_camino"}]
    return [pedido_a_dict(pedido, usuario.rol) for pedido in pedidos]


@router.get("/pedidos/{pedido_id}")
def obtener_pedido(
    pedido_id: int,
    db: Session = Depends(obtener_db),
    usuario=Depends(exigir_roles("administrador", "despachante")),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido_a_dict(pedido, usuario.rol)


@router.put("/pedidos/{pedido_id}/estado")
def cambiar_estado(
    pedido_id: int,
    nuevo_estado: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(obtener_db),
    usuario=Depends(exigir_roles("administrador", "preparador", "despachante")),
):
    estados_validos = {"pendiente", "preparando", "listo_para_despacho", "en_camino", "entregado", "cancelado"}
    if nuevo_estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado no válido")

    pedido = pedido_editable(db, pedido_id)
    if pedido.estado == "cancelado":
        raise HTTPException(status_code=409, detail="Ese pedido ya está cancelado")
    if nuevo_estado == "cancelado":
        if usuario.rol != "administrador":
            raise HTTPException(status_code=403, detail="Solo el administrador puede cancelar pedidos")
        if pedido.estado in {"en_camino", "entregado"}:
            raise HTTPException(status_code=409, detail="No se puede cancelar un pedido que ya salió a reparto")
        reponer_detalles(db, pedido, usuario.nombre_usuario, "Cancelación completa desde el panel")
        pedido.estado = "cancelado"
        db.commit()
        db.refresh(pedido)
        background_tasks.add_task(notificar_estado, pedido.telegram_user_id, pedido.id, pedido.estado)
        return {"mensaje": "Pedido cancelado y stock repuesto", "pedido_id": pedido.id, "estado": pedido.estado}

    if usuario.rol == "preparador":
        puede_preparar = nuevo_estado == "preparando" and pedido.estado in {"pendiente", "preparando"}
        puede_dejar_listo = nuevo_estado == "listo_para_despacho" and pedido.estado in {"preparando", "listo_para_despacho"}
        if not (puede_preparar or puede_dejar_listo):
            raise HTTPException(status_code=403, detail="El preparador solo puede preparar pedidos y dejarlos listos para despacho")
    if usuario.rol == "despachante":
        puede_salir = nuevo_estado == "en_camino" and pedido.estado in {"listo_para_despacho", "en_camino"}
        puede_entregar = nuevo_estado == "entregado" and pedido.estado == "en_camino"
        if not (puede_salir or puede_entregar):
            raise HTTPException(status_code=403, detail="El despachante solo puede marcar pedidos listos en camino o entregados")
        if nuevo_estado in {"en_camino", "entregado"} and pedido.metodo_pago == "Transferencia" and not pedido.pago_verificado:
            raise HTTPException(status_code=403, detail="Primero hay que revisar y verificar el comprobante de transferencia")

    transiciones = {"pendiente": {"preparando"}, "preparando": {"listo_para_despacho"},
                    "listo_para_despacho": {"en_camino"}, "en_camino": {"entregado"}}
    if nuevo_estado != pedido.estado and nuevo_estado not in transiciones.get(pedido.estado, set()):
        raise HTTPException(409, "El pedido debe avanzar en orden: pendiente, preparación, listo, en camino y entregado")
    if nuevo_estado in {"en_camino", "entregado"} and pedido.metodo_pago == "Transferencia" and not pedido.pago_verificado:
        raise HTTPException(403, "Primero hay que verificar la transferencia")
    pedido.estado = nuevo_estado
    db.commit()
    db.refresh(pedido)
    # La llamada a Telegram puede tardar varios segundos si hay problemas de red.
    # Ejecutarla después de responder evita que el clic del panel quede esperando.
    background_tasks.add_task(notificar_estado, pedido.telegram_user_id, pedido.id, pedido.estado)
    return {"mensaje": "Estado actualizado correctamente", "pedido_id": pedido.id, "estado": pedido.estado}


@router.post("/pedidos/{pedido_id}/cancelacion-parcial")
def quitar_productos(pedido_id: int, datos: CancelacionParcial, background_tasks: BackgroundTasks,
                    db: Session = Depends(obtener_db), usuario=Depends(exigir_roles("administrador", "preparador"))):
    registro_id = cancelar_parcial(db, pedido_id, datos.detalle_id, datos.cantidad,
                                  datos.motivo, datos.reponer_stock, usuario.nombre_usuario)
    background_tasks.add_task(enviar_evento, registro_id)
    return {"mensaje": "Productos quitados. El resto del pedido sigue en curso; consultá el estado del aviso en el historial.", "evento_id": registro_id}


@router.post("/pedidos/{pedido_id}/incidencias-delivery")
def informar_delivery(pedido_id: int, datos: IncidenciaDelivery, background_tasks: BackgroundTasks,
                     db: Session = Depends(obtener_db), usuario=Depends(exigir_roles("administrador", "despachante"))):
    pedido = pedido_editable(db, pedido_id)
    if pedido.estado not in {"listo_para_despacho", "en_camino"}:
        raise HTTPException(409, "Las novedades del delivery corresponden a pedidos listos o en camino")
    registro = evento(db, pedido, "delivery", "Novedad del delivery: " + motivo_valido(datos.motivo), usuario.nombre_usuario)
    db.commit()
    background_tasks.add_task(enviar_evento, registro.id)
    return {"mensaje": "Novedad guardada y aviso a Telegram en proceso", "evento_id": registro.id}


@router.post("/pedidos/{pedido_id}/eventos/{evento_id}/reenviar")
def reenviar_aviso(pedido_id: int, evento_id: int, background_tasks: BackgroundTasks,
                  db: Session = Depends(obtener_db), _usuario=Depends(exigir_roles("administrador", "preparador", "despachante"))):
    registro = db.query(EventoPedido).filter(EventoPedido.id == evento_id, EventoPedido.pedido_id == pedido_id).first()
    if not registro:
        raise HTTPException(404, "Aviso no encontrado")
    background_tasks.add_task(enviar_evento, registro.id)
    return {"mensaje": "Reintento solicitado; el historial indicará si Telegram lo recibió"}


@router.put("/pedidos/{pedido_id}/pago-verificado")
def verificar_pago(
    pedido_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador", "despachante")),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    jornada = db.query(Jornada).filter(Jornada.id == pedido.jornada_id).first() if pedido.jornada_id else None
    if jornada and jornada.cerrada_en is not None:
        raise HTTPException(status_code=409, detail="Ese pedido pertenece a un día finalizado y quedó archivado")
    if pedido.metodo_pago != "Transferencia" or not pedido.comprobante_file_id:
        raise HTTPException(status_code=400, detail="El pedido no tiene un comprobante de transferencia para revisar")
    pedido.pago_verificado = True
    db.commit()
    background_tasks.add_task(notificar_pago_verificado, pedido.telegram_user_id, pedido.id)
    return {"mensaje": "Transferencia marcada como verificada", "pedido_id": pedido.id}


@router.get("/pedidos/{pedido_id}/comprobante")
def obtener_comprobante(
    pedido_id: int,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador", "despachante")),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if not pedido.comprobante_file_id:
        raise HTTPException(status_code=404, detail="El pedido no tiene comprobante")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="No está configurado el acceso a Telegram para recuperar el comprobante")

    try:
        query = urlencode({"file_id": pedido.comprobante_file_id})
        with urlopen(f"https://api.telegram.org/bot{token}/getFile?{query}", timeout=10) as respuesta:
            datos = json.loads(respuesta.read())
        if not datos.get("ok") or not datos.get("result", {}).get("file_path"):
            raise ValueError("Telegram no devolvió el archivo")
        ruta = quote(datos["result"]["file_path"], safe="/")
        with urlopen(f"https://api.telegram.org/file/bot{token}/{ruta}", timeout=20) as archivo:
            contenido = archivo.read(20 * 1024 * 1024 + 1)
        if len(contenido) > 20 * 1024 * 1024:
            raise ValueError("El comprobante supera el límite permitido")
    except Exception:
        raise HTTPException(status_code=502, detail="No pude recuperar el comprobante desde Telegram")

    return Response(
        content=contenido,
        media_type=pedido.comprobante_mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="comprobante-{pedido.id}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
