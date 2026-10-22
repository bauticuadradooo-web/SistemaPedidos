"""Creación de copias consistentes de la base SQLite del comercio."""
from datetime import datetime
from html import escape
from pathlib import Path
import sqlite3

from app.database import engine


def crear_informe_pedidos(copia: Path) -> Path:
    """Crea junto a una copia SQLite un informe de pedidos fácil de leer."""
    with sqlite3.connect(copia) as db:
        columnas = {fila[1] for fila in db.execute("PRAGMA table_info(pedidos)")}
        costo_envio = "COALESCE(p.costo_envio, 0)" if "costo_envio" in columnas else "0"
        fecha = "j.fecha" if "jornada_id" in columnas else "NULL"
        join_jornada = "LEFT JOIN jornadas j ON j.id = p.jornada_id" if "jornada_id" in columnas else ""
        pedidos = db.execute(
            f"""SELECT p.id, {fecha}, p.cliente, p.direccion, p.telefono,
                       p.estado, p.metodo_pago, p.total, {costo_envio}
                FROM pedidos p {join_jornada}
                ORDER BY p.id DESC"""
        ).fetchall()
        detalles_por_pedido = {}
        for pedido_id, nombre, cantidad, precio in db.execute(
            """SELECT d.pedido_id, COALESCE(p.nombre, 'Producto eliminado'), d.cantidad, d.precio
               FROM detalle_pedidos d
               LEFT JOIN productos p ON p.id = d.producto_id
               ORDER BY d.pedido_id, d.id"""
        ):
            detalles_por_pedido.setdefault(pedido_id, []).append(
                f"{cantidad} × {escape(str(nombre))} (${float(precio):,.0f} c/u)"
                .replace(",", ".")
            )

    def celda(valor):
        return escape("—" if valor is None or valor == "" else str(valor))

    def dinero(valor):
        return "$" + f"{float(valor or 0):,.0f}".replace(",", ".")

    filas = []
    for pedido_id, fecha_pedido, cliente, direccion, telefono, estado, pago, total, envio in pedidos:
        productos = "<br>".join(detalles_por_pedido.get(pedido_id, [])) or "—"
        filas.append(
            "<tr>"
            f"<td>#{pedido_id}</td><td>{celda(fecha_pedido)}</td><td>{celda(cliente)}</td>"
            f"<td>{celda(direccion)}<br>{celda(telefono)}</td><td>{productos}</td>"
            f"<td>{celda(estado)}</td><td>{celda(pago)}</td>"
            f"<td>{dinero(total)}</td><td>{dinero(envio)}</td></tr>"
        )
    tabla = "".join(filas) or '<tr><td colspan="9">Esta copia no contiene pedidos.</td></tr>'
    documento = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pedidos de la copia de seguridad</title><style>
body{{font:15px Segoe UI,Arial,sans-serif;margin:28px;background:#f4f6f8;color:#17202a}}
h1{{color:#174c3c}}p{{color:#53616d}}.tabla{{overflow-x:auto;background:white;border-radius:10px;padding:12px}}
table{{border-collapse:collapse;width:100%;min-width:1000px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #e5e9ec;vertical-align:top}}
th{{background:#e8f2ed;color:#174c3c;position:sticky;top:0}}tr:hover{{background:#f8fbf9}}
</style></head><body><h1>Pedidos de la copia de seguridad</h1>
<p>Informe de lectura. Para restaurar el sistema completo, conservá también el archivo .sqlite3 de esta carpeta.</p>
<div class="tabla"><table><thead><tr><th>Pedido</th><th>Fecha</th><th>Cliente</th><th>Entrega</th><th>Productos</th><th>Estado</th><th>Pago</th><th>Total</th><th>Envío</th></tr></thead>
<tbody>{tabla}</tbody></table></div></body></html>"""
    informe = copia.with_suffix(".html")
    informe.write_text(documento, encoding="utf-8")
    return informe


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
    informe = destino.with_suffix(".html")
    try:
        with sqlite3.connect(origen) as fuente, sqlite3.connect(destino) as copia:
            fuente.backup(copia)
        crear_informe_pedidos(destino)
        return {
            "nombre": nombre,
            "ubicacion": str(destino.relative_to(Path.cwd())),
            "informe": str(informe.relative_to(Path.cwd())),
            "bytes": destino.stat().st_size,
        }
    except Exception:
        destino.unlink(missing_ok=True)
        informe.unlink(missing_ok=True)
        raise
