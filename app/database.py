import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/pedidos_comercio.db")

def normalizar_database_url(url: str) -> str:
    """Selecciona psycopg 3 para URLs PostgreSQL de distintos proveedores."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


DATABASE_URL = normalizar_database_url(DATABASE_URL)

opciones_engine = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite:"):
    opciones_engine["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    **opciones_engine,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

