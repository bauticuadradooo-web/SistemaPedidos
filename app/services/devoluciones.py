"""Registro de devoluciones ya hechas por el comercio y envío del recibo."""
from datetime import datetime, timedelta
import os
import re

from fastapi import HTTPException
import httpx
from sqlalchemy import or_

from app.database import SessionLocal
from app.models import DevolucionPedido, EventoPedido, Pedido
from app.services.cambios import iniciar_escritura


def validar_alias(valor):
    valor = valor.strip()
    # Validación de formato básico: no certifica titularidad ni existencia bancaria.
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,80}', valor):
        raise HTTPException(422, "Enviá el alias de tu cuenta o el CBU/CVU, sin espacios")
    return valor


def guardar_alias_cliente(db, pedido_id, telegram_id, alias):
    alias = validar_alias(alias)
    iniciar_escritura(db)
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.telegram_user_id == str(telegram_id)).with_for_update().first()
    if not pedido:
        raise HTTPException(404, "No encontré ese pedido asociado a tu cuenta")
    if pedido.metodo_pago != "Transferencia":
        raise HTTPException(409, "Ese pedido no se pagó por transferencia")
    if db.query(DevolucionPedido).filter_by(pedido_id=pedido.id).first():
        raise HTTPException(409, "La devolución ya fue registrada; contactá al comercio")
    pedido.alias_cliente = alias
    db.commit()


def cancelado_por_cliente(db, pedido):
    return pedido.estado == 'cancelado' and pedido.metodo_pago == 'Transferencia' and bool(pedido.comprobante_file_id) and bool(
        db.query(EventoPedido.id).filter_by(pedido_id=pedido.id, tipo='cancelacion_cliente').first())


def enviar_comprobante_devolucion(devolucion_id):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        return False
    ahora = datetime.utcnow()
    with SessionLocal() as db:
        registro = db.get(DevolucionPedido, devolucion_id)
        if not registro:
            return False
        if registro.enviado_telegram:
            return True
        pedido = db.get(Pedido, registro.pedido_id)
        if not pedido or not pedido.telegram_user_id:
            return False
        # Reclamar el envío sin mantener un bloqueo SQLite durante la llamada de red.
        reclamado = db.query(DevolucionPedido).filter(
            DevolucionPedido.id == devolucion_id, DevolucionPedido.enviado_telegram.is_(False),
            or_(DevolucionPedido.envio_iniciado_en.is_(None), DevolucionPedido.envio_iniciado_en < ahora - timedelta(minutes=2)),
        ).update({DevolucionPedido.envio_iniciado_en: ahora}, synchronize_session=False)
        db.commit()
        if not reclamado:
            return False
        archivo = registro.comprobante
        nombre = registro.nombre_archivo
        mime = registro.mime_type
        chat_id = pedido.telegram_user_id
        caption = (f"Devolución del pedido #{pedido.id}\n"
                   f"El comercio registró una devolución de ${registro.importe:,.2f} a la cuenta {registro.alias_destino}.\n"
                   "Te adjuntamos el comprobante. Revisá el movimiento en tu cuenta; si no aparece, contactá al comercio.")
    enviado = False
    try:
        respuesta = httpx.post(f'https://api.telegram.org/bot{token}/sendDocument',
                               data={'chat_id': chat_id, 'caption': caption},
                               files={'document': (nombre, archivo, mime)}, timeout=20)
        respuesta.raise_for_status()
        enviado = respuesta.json().get('ok') is True
    except (httpx.HTTPError, ValueError):
        pass
    finally:
        with SessionLocal() as db:
            db.query(DevolucionPedido).filter(DevolucionPedido.id == devolucion_id,
                DevolucionPedido.envio_iniciado_en == ahora).update({
                    DevolucionPedido.enviado_telegram: enviado,
                    DevolucionPedido.envio_iniciado_en: None,
                }, synchronize_session=False)
            db.commit()
    return enviado
