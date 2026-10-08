import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    SESSION_HOURS,
    crear_sesion,
    hash_password,
    hash_token,
    obtener_db,
    obtener_usuario_actual,
    verificar_password,
)
from app.models import SesionPanel, UsuarioPanel

router = APIRouter(prefix="/auth", tags=["autenticación"])


class CredencialNueva(BaseModel):
    nombre_usuario: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=200)


class ConfiguracionInicial(BaseModel):
    administrador: CredencialNueva
    preparador: CredencialNueva
    despachante: CredencialNueva


class InicioSesion(BaseModel):
    nombre_usuario: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


def fijar_cookie(response: Response, request: Request, token: str):
    secure = os.getenv("PANEL_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_HOURS * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


@router.get("/status")
def estado_configuracion(db: Session = Depends(obtener_db)):
    return {"configurado": db.query(UsuarioPanel).count() == 3}


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def configurar_cuentas(
    datos: ConfiguracionInicial,
    request: Request,
    response: Response,
    db: Session = Depends(obtener_db),
):
    if db.query(UsuarioPanel).count() != 0:
        raise HTTPException(status_code=409, detail="Las cuentas ya están configuradas")

    cuentas = [
        ("administrador", datos.administrador),
        ("preparador", datos.preparador),
        ("despachante", datos.despachante),
    ]
    nombres = [cuenta.nombre_usuario.strip().lower() for _, cuenta in cuentas]
    if len(set(nombres)) != 3:
        raise HTTPException(status_code=422, detail="Cada rol necesita un nombre de usuario diferente")

    usuarios = {}
    for rol, cuenta in cuentas:
        nombre = cuenta.nombre_usuario.strip().lower()
        sal, digest = hash_password(cuenta.password)
        usuario = UsuarioPanel(
            nombre_usuario=nombre,
            rol=rol,
            sal_password=sal,
            hash_password=digest,
        )
        db.add(usuario)
        usuarios[rol] = usuario

    db.flush()
    token = crear_sesion(db, usuarios["administrador"])
    db.commit()
    fijar_cookie(response, request, token)
    return {"mensaje": "Las tres cuentas quedaron configuradas"}


@router.post("/login")
def iniciar_sesion(
    datos: InicioSesion,
    request: Request,
    response: Response,
    db: Session = Depends(obtener_db),
):
    nombre = datos.nombre_usuario.strip().lower()
    usuario = db.query(UsuarioPanel).filter(UsuarioPanel.nombre_usuario == nombre).first()
    if not usuario or not usuario.activo or not verificar_password(datos.password, usuario.sal_password, usuario.hash_password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    db.query(SesionPanel).filter(SesionPanel.expira_en <= datetime.utcnow()).delete()
    token = crear_sesion(db, usuario)
    db.commit()
    fijar_cookie(response, request, token)
    return {"mensaje": "Sesión iniciada", "rol": usuario.rol}


@router.post("/logout")
def cerrar_sesion(request: Request, response: Response, db: Session = Depends(obtener_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.query(SesionPanel).filter(SesionPanel.token_hash == hash_token(token)).delete()
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return {"mensaje": "Sesión cerrada"}


@router.get("/me")
def identidad_actual(usuario: UsuarioPanel = Depends(obtener_usuario_actual)):
    return {"nombre_usuario": usuario.nombre_usuario, "rol": usuario.rol}
