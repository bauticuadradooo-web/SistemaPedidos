"""Copia datos locales a una base PostgreSQL vacía, conservando sus IDs.

Usa DATABASE_URL solo para el destino. La sesión del panel se omite para
obligar a todos a iniciar sesión de nuevo en el sitio publicado.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.engine import URL
from sqlalchemy.types import Integer

load_dotenv()

from app.database import Base, normalizar_database_url
from app import models  # Registra las tablas en Base.metadata.


def migrar():
    ruta_origen = Path(os.getenv("LOCAL_DATABASE_PATH", "database/pedidos_comercio.db"))
    if not ruta_origen.is_absolute():
        ruta_origen = (Path.cwd() / ruta_origen).resolve()
    if not ruta_origen.is_file():
        raise SystemExit(f"No encontré la base local: {ruta_origen}")

    url_destino = os.getenv("CLOUD_DATABASE_URL", "").strip()
    if not url_destino:
        raise SystemExit("Definí CLOUD_DATABASE_URL en esta terminal con la conexión de PostgreSQL.")
    url_destino = normalizar_database_url(url_destino)
    engine_origen = create_engine(URL.create("sqlite", database=str(ruta_origen)))
    engine_destino = create_engine(url_destino, pool_pre_ping=True)
    if engine_destino.dialect.name != "postgresql":
        raise SystemExit("CLOUD_DATABASE_URL debe apuntar a PostgreSQL.")

    Base.metadata.create_all(bind=engine_destino)
    tablas = list(Base.metadata.sorted_tables)
    tablas_datos = [tabla for tabla in tablas if tabla.name != "sesiones_panel"]

    try:
        with engine_origen.connect() as origen, engine_destino.begin() as destino:
            # Permite únicamente la jornada vacía que la app crea al arrancar.
            tablas_con_datos = []
            for tabla in tablas:
                cantidad = destino.execute(select(func.count()).select_from(tabla)).scalar_one()
                if cantidad:
                    tablas_con_datos.append((tabla, cantidad))
            permitida = {"jornadas"}
            if any(tabla.name not in permitida for tabla, _ in tablas_con_datos):
                nombres = ", ".join(f"{tabla.name} ({cantidad})" for tabla, cantidad in tablas_con_datos)
                raise SystemExit(f"La base PostgreSQL ya tiene datos y no está vacía: {nombres}")
            for tabla, _ in tablas_con_datos:
                destino.execute(tabla.delete())

            for tabla in tablas_datos:
                filas = [dict(fila) for fila in origen.execute(select(tabla)).mappings()]
                if filas:
                    destino.execute(insert(tabla), filas)
                    print(f"{tabla.name}: {len(filas)} registro(s) copiados")
                clave = next(iter(tabla.primary_key.columns), None)
                if clave is not None and isinstance(clave.type, Integer):
                    secuencia = destino.execute(
                        text("SELECT pg_get_serial_sequence(:tabla, :columna)"),
                        {"tabla": tabla.name, "columna": clave.name},
                    ).scalar_one_or_none()
                    maximo = destino.execute(select(func.max(clave))).scalar_one_or_none()
                    if secuencia and maximo is not None:
                        destino.execute(
                            text("SELECT setval(:secuencia, :maximo, true)"),
                            {"secuencia": secuencia, "maximo": maximo},
                        )

        print("Migración finalizada. Las sesiones antiguas no se copiaron; iniciá sesión de nuevo en la web.")
    finally:
        engine_origen.dispose()
        engine_destino.dispose()


if __name__ == "__main__":
    migrar()
