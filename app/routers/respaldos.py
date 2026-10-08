from fastapi import APIRouter, Depends, HTTPException

from app.auth import exigir_roles
from app.services.backups import crear_respaldo

router = APIRouter(prefix="/respaldos", tags=["respaldos"])


@router.post("/crear")
def crear_copia(_usuario=Depends(exigir_roles("administrador"))):
    try:
        return crear_respaldo()
    except Exception as error:
        raise HTTPException(status_code=500, detail="No se pudo crear la copia de seguridad") from error
