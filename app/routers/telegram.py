import os

from fastapi import APIRouter

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/estado")
def estado_bot():
    return {
        "configurado": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "modo": "long_polling",
        "instruccion": "Iniciá el proceso con python -m app.telegram_bot",
    }
