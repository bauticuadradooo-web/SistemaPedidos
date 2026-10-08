"""Creación de copias consistentes de la base SQLite del comercio."""
from datetime import datetime
from pathlib import Path
import sqlite3

from app.database import engine


def crear_respaldo() -> dict:
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Las copias locales están configuradas para SQLite")

    origen = Path(engine.url.database or "").expanduser()
    if not origen.is_absolute():
        origen = (Path.cwd() / origen).resolve()
    if not origen.is_file():
        raise FileNotFoundError("No se encontró la base de datos para respaldar")

    carpeta = origen.parent / "backups"
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"{origen.stem}_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3"
    destino = carpeta / nombre
    try:
        with sqlite3.connect(origen) as fuente, sqlite3.connect(destino) as copia:
            fuente.backup(copia)
        return {
            "nombre": nombre,
            "ubicacion": str(destino.relative_to(Path.cwd())),
            "bytes": destino.stat().st_size,
        }
    except Exception:
        destino.unlink(missing_ok=True)
        raise
