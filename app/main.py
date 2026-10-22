from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import inspect, text
from dotenv import load_dotenv

load_dotenv()

from app.database import engine, Base, SessionLocal
from app import models
from app.auth import usuario_de_sesion, SESSION_COOKIE
from app.services.jornadas import jornada_actual
from app.routers import auth, jornadas, pedidos, productos, respaldos, telegram, devoluciones

Base.metadata.create_all(bind=engine)

# Agrega la columna a bases SQLite creadas con una versión anterior.
if "telegram_user_id" not in {c["name"] for c in inspect(engine).get_columns("pedidos")}:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE pedidos ADD COLUMN telegram_user_id VARCHAR"))

columnas_pedido = {c["name"] for c in inspect(engine).get_columns("pedidos")}
for nombre_columna, tipo_sql in [
    ("monto_efectivo", "FLOAT"),
    ("comprobante_file_id", "VARCHAR"),
    ("comprobante_mime_type", "VARCHAR"),
    ("comprobante_nombre", "VARCHAR"),
    ("pago_verificado", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("zona_entrega", "VARCHAR"),
    ("costo_envio", "FLOAT NOT NULL DEFAULT 0"),
    ("alias_cliente", "VARCHAR(80)"),
]:
    if nombre_columna not in columnas_pedido:
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE pedidos ADD COLUMN {nombre_columna} {tipo_sql}"))
        columnas_pedido.add(nombre_columna)

if "jornada_id" not in columnas_pedido:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE pedidos ADD COLUMN jornada_id INTEGER REFERENCES jornadas(id)"))

# La app anterior no guardaba la jornada de cada pedido. Conservamos todos
# los registros existentes dentro de la primera jornada disponible.
with SessionLocal() as db:
    jornada = jornada_actual(db)
    db.query(models.Pedido).filter(models.Pedido.jornada_id.is_(None)).update(
        {models.Pedido.jornada_id: jornada.id}, synchronize_session=False
    )
    db.commit()

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
def inicio(request: Request):
    with SessionLocal() as db:
        cuentas_configuradas = db.query(models.UsuarioPanel).count() >= 3
        usuario = usuario_de_sesion(db, request.cookies.get(SESSION_COOKIE))
    nombre_archivo = "index.html" if cuentas_configuradas and usuario else "login.html"
    return FileResponse(
        Path(__file__).parent / "templates" / nombre_archivo,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


app.include_router(auth.router)
app.include_router(jornadas.router)
app.include_router(pedidos.router)
app.include_router(productos.router)
app.include_router(telegram.router)
app.include_router(respaldos.router)
app.include_router(devoluciones.router)
