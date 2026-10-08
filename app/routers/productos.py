from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.auth import exigir_roles
from app.models import Producto

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
    _usuario=Depends(exigir_roles("administrador")),
):
    productos = db.query(Producto).all()

    return productos


@router.put("/productos/{producto_id}")
def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.nombre = datos.nombre.strip()
    if not producto.nombre:
        raise HTTPException(status_code=422, detail="El nombre del producto no puede quedar vacío")
    producto.precio = datos.precio
    producto.stock = datos.stock
    db.commit()
    db.refresh(producto)
    return producto


@router.patch("/productos/{producto_id}/stock")
def ajustar_stock(
    producto_id: int,
    ajuste: AjusteStock,
    db: Session = Depends(obtener_db),
    _usuario=Depends(exigir_roles("administrador")),
):
    if ajuste.delta == 0:
        raise HTTPException(status_code=422, detail="El ajuste de stock debe ser distinto de cero")
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    nuevo_stock = producto.stock + ajuste.delta
    if nuevo_stock < 0:
        raise HTTPException(status_code=422, detail="El stock no puede ser menor que cero")

    producto.stock = nuevo_stock
    db.commit()
    db.refresh(producto)
    return producto
