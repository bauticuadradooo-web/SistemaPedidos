"""Autenticación y permisos del panel del comercio."""
from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import SesionPanel, UsuarioPanel

SESSION_COOKIE = "dely_panel_session"
SESSION_HOURS = 12


def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 310_000)
    return salt, digest.hex()


def verificar_password(password: str, salt: str, expected_hash: str) -> bool:
    _, actual_hash = hash_password(password, salt)
    return secrets.compare_digest(actual_hash, expected_hash)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def crear_sesion(db: Session, usuario: UsuarioPanel) -> str:
    token = secrets.token_urlsafe(32)
    db.add(SesionPanel(
        token_hash=hash_token(token),
        usuario_id=usuario.id,
        expira_en=datetime.utcnow().replace(microsecond=0) + timedelta(hours=SESSION_HOURS),
    ))
    return token


def usuario_de_sesion(db: Session, token: str | None) -> UsuarioPanel | None:
    if not token:
        return None
    sesion = db.query(SesionPanel).filter(
        SesionPanel.token_hash == hash_token(token),
        SesionPanel.expira_en > datetime.utcnow(),
    ).first()
    if not sesion or not sesion.usuario.activo:
        return None
    return sesion.usuario


def obtener_usuario_actual(
    request: Request,
    db: Session = Depends(obtener_db),
) -> UsuarioPanel:
    usuario = usuario_de_sesion(db, request.cookies.get(SESSION_COOKIE))
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Iniciá sesión para continuar")
    return usuario


def exigir_roles(*roles: str):
    def verificar_rol(usuario: UsuarioPanel = Depends(obtener_usuario_actual)) -> UsuarioPanel:
        if usuario.rol not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés permiso para esta acción")
        return usuario

    return verificar_rol
