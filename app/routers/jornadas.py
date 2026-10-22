from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import exigir_roles
from app.database import SessionLocal
from app.models import Jornada, Pedido
from app.routers.pedidos import pedido_a_dict
from app.services.jornadas import jornada_actual
from app.services.backups import crear_respaldo

router = APIRouter(prefix="/jornadas", tags=["jornadas"])


def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/actual")
def obtener_jornada_actual(
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    jornada = jornada_actual(db)
    pedidos = db.query(Pedido).filter(Pedido.jornada_id == jornada.id).all()
    entregados = [pedido for pedido in pedidos if pedido.estado == "entregado"]
    return {
        "id": jornada.id,
        "fecha": jornada.fecha.isoformat(),
        "cantidad_pedidos": len(pedidos),
        "pedidos_pendientes": sum(pedido.estado not in {"entregado", "cancelado"} for pedido in pedidos),
        "ventas_entregadas": len(entregados),
        "total_ventas": sum(pedido.total for pedido in entregados),
    }


@router.get("/historial")
def listar_jornadas_finalizadas(
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    jornadas = (
        db.query(Jornada)
        .filter(Jornada.cerrada_en.is_not(None))
        .order_by(Jornada.id.desc())
        .all()
    )
    return [
        {
            "id": jornada.id,
            "fecha": jornada.fecha.isoformat(),
            "cerrada_en": jornada.cerrada_en.isoformat() if jornada.cerrada_en else None,
            "cantidad_pedidos": jornada.cantidad_pedidos,
            "total_ventas": jornada.total_ventas,
        }
        for jornada in jornadas
    ]


@router.get("/{jornada_id}/pedidos")
def pedidos_de_jornada(
    jornada_id: int,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    jornada = db.query(Jornada).filter(Jornada.id == jornada_id).first()
    if not jornada or jornada.cerrada_en is None:
        raise HTTPException(status_code=404, detail="No encontré ese día finalizado")
    pedidos = (
        db.query(Pedido)
        .filter(Pedido.jornada_id == jornada.id)
        .order_by(Pedido.id)
        .all()
    )
    return [pedido_a_dict(pedido, "administrador") for pedido in pedidos]


@router.post("/finalizar")
def finalizar_jornada(
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    jornada = jornada_actual(db)
    pedidos = db.query(Pedido).filter(Pedido.jornada_id == jornada.id).all()
    sin_entregar = [pedido for pedido in pedidos if pedido.estado not in {"entregado", "cancelado"}]
    if sin_entregar:
        raise HTTPException(
            status_code=409,
            detail=f"Quedan {len(sin_entregar)} pedido(s) sin entregar. Completalos antes de finalizar el día.",
        )

    jornada.cantidad_pedidos = len(pedidos)
    jornada.total_ventas = sum(pedido.total for pedido in pedidos if pedido.estado == "entregado")
    jornada.cerrada_en = datetime.now()
    db.flush()

    proxima = Jornada(
        fecha=jornada.fecha + timedelta(days=1),
        iniciada_en=datetime.now(),
    )
    db.add(proxima)
    db.commit()
    db.refresh(proxima)
    try:
        respaldo = crear_respaldo()
        nombre_respaldo = respaldo["nombre"]
        informe_respaldo = respaldo["informe"]
        aviso_respaldo = None
    except Exception:
        nombre_respaldo = None
        informe_respaldo = None
        aviso_respaldo = "No se pudo crear la copia automática; usá Copia de seguridad en el panel."
    return {
        "mensaje": "Día finalizado. Se archivaron sus pedidos y ventas.",
        "fecha_finalizada": jornada.fecha.isoformat(),
        "cantidad_pedidos": jornada.cantidad_pedidos,
        "total_ventas": jornada.total_ventas,
        "proxima_fecha": proxima.fecha.isoformat(),
        "respaldo": nombre_respaldo,
        "informe_respaldo": informe_respaldo,
        "aviso_respaldo": aviso_respaldo,
    }
