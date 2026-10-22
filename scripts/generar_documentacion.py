r"""Exporta índice de código, esquema sin filas y diagrama para estudiar el proyecto.

No inicia la app ni consulta datos de clientes. Uso desde la raíz:
  .venv\Scripts\python.exe scripts/generar_documentacion.py
"""
import ast
import argparse
from datetime import date
from html import escape
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


def indice_codigo():
    partes = ['# Índice de clases y funciones', '',
              'Generado desde los archivos Python. La línea es la del código revisado; puede cambiar si se edita el archivo.', '',
              'Para entender las responsabilidades, leer primero [la guía del código](02_GUIA_DEL_CODIGO.md). Este índice sirve para ubicar cada símbolo.', '']
    for carpeta in ('app', 'scripts', 'tests'):
        for archivo in sorted((ROOT / carpeta).rglob('*.py')):
            ruta = archivo.relative_to(ROOT).as_posix()
            arbol = ast.parse(archivo.read_text(encoding='utf-8-sig'))
            partes += [f'## `{ruta}`', '', f'[Abrir archivo](../{ruta})', '']
            if not arbol.body:
                partes += ['Archivo de inicialización del paquete Python; no contiene lógica de negocio.', '']
                continue
            doc = ast.get_docstring(arbol)
            if doc:
                partes += [doc.split('\n')[0], '']
            partes += ['| Símbolo | Línea | Descripción o firma |', '| --- | --- | --- |']
            contador = 0

            def recorrer(nodos, prefijo=''):
                nonlocal contador
                for nodo in nodos:
                    if isinstance(nodo, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        nombre = prefijo + nodo.name
                        if isinstance(nodo, ast.ClassDef):
                            descripcion = 'Clase' + (': ' + ', '.join(ast.unparse(x) for x in nodo.bases) if nodo.bases else '')
                        else:
                            descripcion = ('async ' if isinstance(nodo, ast.AsyncFunctionDef) else '') + f'{nodo.name}({ast.unparse(nodo.args)})'
                        doc_funcion = ast.get_docstring(nodo)
                        if doc_funcion:
                            descripcion += ' — ' + doc_funcion.split('\n')[0]
                        descripcion = descripcion.replace('|', '\\|').replace('\n', ' ')
                        partes.append(f'| `{nombre}` | {nodo.lineno} | {descripcion} |')
                        contador += 1
                        recorrer(nodo.body, nombre + '.')
            recorrer(arbol.body)
            if not contador:
                partes.append('| — | — | Configuración o código ejecutado al importar el módulo. |')
            partes.append('')
    (DOCS / 'INDICE_DEL_CODIGO.md').write_text('\n'.join(partes), encoding='utf-8')


def esquema_sqlite(base=None):
    base = Path(base) if base else ROOT / 'database' / 'pedidos_comercio.db'
    if not base.is_file():
        print('Sin base local: se conserva el esquema SQL ya exportado, si existe.')
        return
    with sqlite3.connect(base.resolve().as_uri() + '?mode=ro', uri=True) as db:
        filas = db.execute("""SELECT type, name, sql FROM sqlite_master
            WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL
            ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name""").fetchall()
    texto = (f'-- Estructura SQLite exportada el {date.today():%Y-%m-%d}.\n'
             '-- Sin filas, credenciales, datos de clientes ni comprobantes.\n'
             '-- Material de estudio: no ejecutar sobre la base de trabajo existente.\n\n')
    texto += '\n\n'.join(f'-- {tipo}: {nombre}\n{sql};' for tipo, nombre, sql in filas) + '\n'
    (DOCS / 'esquema_sqlite.sql').write_text(texto, encoding='utf-8')


def diagrama():
    cajas = [
        ('productos', 30, 80, 300, 160, ['PK id', 'nombre · precio', 'stock disponible']),
        ('detalle_pedidos', 30, 340, 300, 180, ['PK id', 'FK pedido_id', 'FK producto_id', 'cantidad · precio de venta']),
        ('jornadas', 470, 40, 300, 150, ['PK id', 'fecha · iniciada_en', 'cerrada_en · resumen de ventas']),
        ('pedidos', 470, 300, 300, 240, ['PK id', 'FK jornada_id (opcional)', 'cliente · entrega · Telegram', 'estado · pago · total', 'comprobante original: file_id', 'alias_cliente']),
        ('movimientos_stock', 30, 690, 300, 190, ['PK id', 'FK producto_id', 'FK pedido_id (opcional)', 'delta · motivo · autor · fecha']),
        ('eventos_pedido', 470, 700, 300, 180, ['PK id', 'FK pedido_id', 'tipo · descripción · autor', 'notificado']),
        ('devoluciones_pedido', 920, 330, 310, 210, ['PK id', 'FK pedido_id (UNIQUE)', 'alias_destino · importe', 'comprobante: bytes', 'enviado_telegram']),
        ('usuarios_panel', 920, 50, 310, 160, ['PK id', 'nombre_usuario (UNIQUE) · rol', 'sal · hash de clave · activo']),
        ('sesiones_panel', 920, 720, 310, 160, ['PK token_hash', 'FK usuario_id', 'expira_en']),
    ]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1300" height="1020" viewBox="0 0 1300 1020">',
           '<title>Relaciones de la base de datos de SistemaPedidos</title>',
           '<desc>Diagrama simplificado de las nueve tablas, con claves primarias y referencias.</desc>',
           '<rect width="1300" height="1020" fill="#f4f7f4"/>',
           '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#223d31}.title{font-size:19px;font-weight:700;fill:white}.field{font-size:16px}.label{font-size:14px;fill:#596c61}</style>',
           '<g fill="none" stroke="#6c8d79" stroke-width="2.5">',
           '<path d="M180 340V240"/>', '<path d="M470 410H330"/>',
           '<path d="M620 300V190"/>', '<path d="M180 690H15V160H30"/>',
           '<path d="M470 490H390V780H330"/>', '<path d="M620 700V540"/>',
           '<path d="M920 430H770"/>', '<path d="M1230 800H1260V130H1230"/>', '</g>',
           '<g class="label"><text x="190" y="290">1 → N</text><text x="355" y="398">1 → N</text>',
           '<text x="635" y="250">1 → N</text><text x="635" y="630">1 → N</text>',
           '<text x="796" y="416">1 → 0..1</text><text x="1248" y="625" transform="rotate(-90 1248 625)">1 → N</text></g>']
    for nombre, x, y, ancho, alto, campos in cajas:
        svg += [f'<rect x="{x}" y="{y}" width="{ancho}" height="{alto}" rx="12" fill="white" stroke="#cddcd1"/>',
                f'<path d="M{x+12} {y}H{x+ancho-12}Q{x+ancho} {y} {x+ancho} {y+12}V{y+44}H{x}V{y+12}Q{x} {y} {x+12} {y}" fill="#245a43"/>',
                f'<text x="{x+15}" y="{y+29}" class="title">{escape(nombre)}</text>']
        for i, campo in enumerate(campos):
            svg.append(f'<text x="{x+15}" y="{y+72+i*27}" class="field">{escape(campo)}</text>')
    svg += ['<text x="30" y="950" style="font-size:19px;font-weight:700">PK = clave primaria · FK = clave foránea · N = muchos</text>',
            '<text x="30" y="980" class="label">Esquema simplificado: consultar 03_BASE_DE_DATOS.md para todos los campos, cardinalidades y límites de integridad.</text>', '</svg>']
    (DOCS / 'diagrama_base.svg').write_text('\n'.join(svg), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Exportar estructura e índice sin datos de clientes')
    parser.add_argument('--base', help='Ruta opcional de una base SQLite para leer su estructura')
    args = parser.parse_args()
    DOCS.mkdir(exist_ok=True)
    indice_codigo()
    esquema_sqlite(args.base)
    diagrama()
    print('Documentación generada en docs/ sin exportar filas de datos.')
