from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.auth import exigir_roles
from app.models import Producto, MovimientoStock
from app.services.cambios import iniciar_escritura, pedido_editable, motivo_valido, evento
from app.services.telegram import enviar_evento

router = APIRouter()


class ProductoCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    precio: float = Field(gt=0)
    stock: int = Field(ge=0)


class ProductoActualizar(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    precio: float = Field(gt=0)
    stock: int = Field(ge=0)


class AjusteStock(BaseModel):
    delta: int
    motivo: str = Field(min_length=3, max_length=1000)
    pedido_id: int | None = Field(default=None, gt=0)


def obtener_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/productos")
def crear_producto(
    producto: ProductoCrear,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    nuevo_producto = Producto(
        nombre=producto.nombre,
        precio=producto.precio,
        stock=producto.stock
    )

    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)

    return nuevo_producto


@router.get("/productos")
def listar_productos(
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador", "preparador")),
    q: str = "",
):
    productos = db.query(Producto).order_by(Producto.nombre).all()
    import unicodedata
    def normalizar(texto):
        return ''.join(c for c in unicodedata.normalize('NFD', texto.casefold()) if not unicodedata.combining(c))
    consulta = normalizar(q.strip())
    return [{"id": p.id, "nombre": p.nombre, "stock": p.stock,
             **({"precio": p.precio} if _usuario.rol == "administrador" else {})}
            for p in productos if not consulta or consulta in normalizar(p.nombre) or consulta == str(p.id)]


@router.put("/productos/{producto_id}")
def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    iniciar_escritura(db)
    producto = db.query(Producto).filter(Producto.id == producto_id).with_for_update().first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.nombre = datos.nombre.strip()
    if not producto.nombre:
        raise HTTPException(status_code=422, detail="El nombre del producto no puede quedar vacío")
    producto.precio = datos.precio
    if producto.stock != datos.stock:
        db.add(MovimientoStock(producto_id=producto.id, delta=datos.stock - producto.stock,
                               motivo="Corrección de inventario por administrador", autor=_usuario.nombre_usuario))
    producto.stock = datos.stock
    db.commit()
    db.refresh(producto)
    return producto


@router.patch("/productos/{producto_id}/stock")
def ajustar_stock(
    producto_id: int,
    ajuste: AjusteStock,
    background_tasks: BackgroundTasks,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador", "preparador")),
):
    motivo = motivo_valido(ajuste.motivo)
    if ajuste.delta == 0:
        raise HTTPException(status_code=422, detail="El ajuste de stock debe ser distinto de cero")
    if _usuario.rol == "preparador" and ajuste.delta > 0:
        raise HTTPException(403, "El preparador solo puede registrar bajas de stock")
    iniciar_escritura(db)
    pedido = pedido_editable(db, ajuste.pedido_id) if ajuste.pedido_id else None
    if pedido and (pedido.estado not in {"pendiente", "preparando", "listo_para_despacho"} or
                   not any(d.producto_id == producto_id for d in pedido.detalles)):
        raise HTTPException(409, "El pedido debe estar activo, antes del reparto, e incluir este producto")
    producto = db.query(Producto).filter(Producto.id == producto_id).with_for_update().first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    nuevo_stock = producto.stock + ajuste.delta
    if nuevo_stock < 0:
        raise HTTPException(status_code=422, detail="El stock no puede ser menor que cero")

    producto.stock = nuevo_stock
    db.add(MovimientoStock(producto_id=producto.id, pedido_id=ajuste.pedido_id, delta=ajuste.delta,
                           motivo=motivo, autor=_usuario.nombre_usuario))
    registro = None
    if pedido:
        registro = evento(db, pedido, "stock", f"Novedad sobre {producto.nombre}: {motivo}\nEl comercio registró un ajuste del stock disponible; los productos y el total de tu pedido no cambiaron.", _usuario.nombre_usuario)
    db.commit()
    db.refresh(producto)
    if registro:
        background_tasks.add_task(enviar_evento, registro.id)
    return {"id": producto.id, "nombre": producto.nombre, "stock": producto.stock}


@router.get("/movimientos-stock")
def historial_stock(db: Session = Depends(obtener_db),
                    _usuario=Depends(exigir_roles("administrador", "preparador"))):
    filas = db.query(MovimientoStock, Producto.nombre).join(Producto).order_by(MovimientoStock.id.desc()).limit(100).all()
    return [{"id": m.id, "producto": nombre, "delta": m.delta, "pedido_id": m.pedido_id,
             "motivo": m.motivo, "autor": m.autor, "fecha": m.creado_en.isoformat() + "Z"} for m, nombre in filas]
