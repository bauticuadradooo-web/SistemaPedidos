import os

import httpx

from app.database import SessionLocal
from app.models import EventoPedido, Pedido


NOMBRES_ESTADO = {
    "pendiente": "pendiente",
    "preparando": "en preparación",
    "listo_para_despacho": "listo para despacho",
    "en_camino": "en camino",
    "entregado": "entregado",
    "cancelado": "cancelado",
}


def enviar_evento(evento_id: int) -> bool:
    """Conserva el aviso pendiente si Telegram falla; el panel permite reintentar."""
    with SessionLocal() as db:
        registro = db.get(EventoPedido, evento_id)
        if not registro:
            return False
        if registro.notificado:
            return True
        pedido = db.get(Pedido, registro.pedido_id)
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token or not pedido or not pedido.telegram_user_id:
            return False
        try:
            respuesta = httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": pedido.telegram_user_id,
                      "text": f"Pedido #{pedido.id}\n{registro.descripcion}"},
                timeout=8,
            )
            respuesta.raise_for_status()
            if not respuesta.json().get("ok"):
                return False
        except (httpx.HTTPError, ValueError):
            return False
        registro.notificado = True
        db.commit()
        return True


def notificar_estado(chat_id: str | None, pedido_id: int, estado: str) -> None:
    """Notifica al cliente cuando el comercio cambia el estado del pedido."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return
    if estado == "entregado":
        texto = f"Tu pedido #{pedido_id} fue entregado. ¡Gracias por elegir Dely Drinks!"
    else:
        texto = f"Actualización del pedido #{pedido_id}: {NOMBRES_ESTADO.get(estado, estado)}."
    try:
        respuesta = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": texto,
            },
            timeout=8,
        )
        respuesta.raise_for_status()
    except httpx.HTTPError:
        # No fallar la actualización del panel si Telegram está temporalmente caído.
        return


def notificar_pago_verificado(chat_id: str | None, pedido_id: int) -> None:
    """Informa al cliente que el comercio revisó el comprobante de transferencia."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return
    try:
        respuesta = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"El comercio revisó y verificó el comprobante del pedido #{pedido_id}.",
            },
            timeout=8,
        )
        respuesta.raise_for_status()
    except httpx.HTTPError:
        return
