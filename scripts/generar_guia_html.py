"""Convierte las cinco guías propias a un documento HTML de lectura e impresión.

Es un conversor pequeño para el subconjunto Markdown usado en estos documentos,
no una biblioteca general ni una parte del servidor de pedidos.
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


def inline(texto):
    fragmentos = []
    def guardar(html):
        fragmentos.append(html)
        return f'\x00{len(fragmentos)-1}\x00'
    texto = re.sub(r'`([^`]+)`', lambda m: guardar(f'<code>{escape(m[1])}</code>'), texto)
    texto = re.sub(r'!\[([^]]*)\]\(([^)]+)\)', lambda m: guardar(f'<img src="{escape(m[2], quote=True)}" alt="{escape(m[1], quote=True)}">'), texto)
    texto = re.sub(r'\[([^]]+)\]\(([^)]+)\)', lambda m: guardar(f'<a href="{escape(m[2], quote=True)}">{escape(m[1])}</a>'), texto)
    texto = escape(texto)
    texto = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', texto)
    texto = re.sub(r'\x00(\d+)\x00', lambda m: fragmentos[int(m[1])], texto)
    return texto


def markdown(texto):
    lineas = texto.splitlines()
    salida = []
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if not linea.strip():
            i += 1
            continue
        if linea.startswith('```'):
            lenguaje = linea[3:].strip()
            i += 1
            bloque = []
            while i < len(lineas) and not lineas[i].startswith('```'):
                bloque.append(lineas[i])
                i += 1
            contenido = '\n'.join(bloque)
            if lenguaje == 'mermaid':
                if 'erDiagram' in contenido:
                    salida.append('<p class="nota">El diagrama superior resume estas relaciones. El Markdown conserva también su versión Mermaid.</p>')
                elif 'flowchart LR' in contenido:
                    salida.append('<div class="flujo">Pendiente → En preparación → Listo para despacho → En camino → Entregado</div><p class="nota">Cancelación del cliente: solo pendiente. Cancelación excepcional del administrador: antes del reparto.</p>')
                else:
                    salida.append('<div class="flujo">Cliente ↔ Telegram ↔ Bot → Servicios → Base de datos<br>Personal ↔ Navegador ↔ API → Servicios / Base de datos<br>API → Avisos → Telegram</div>')
            else:
                salida.append(f'<pre><code>{escape(contenido)}</code></pre>')
            i += 1
            continue
        titulo = re.match(r'^(#{1,6})\s+(.+)', linea)
        if titulo:
            nivel = len(titulo[1])
            salida.append(f'<h{nivel}>{inline(titulo[2])}</h{nivel}>')
            i += 1
            continue
        if linea.startswith('|'):
            filas = []
            while i < len(lineas) and lineas[i].startswith('|'):
                celdas = [x.strip().replace('\\|', '|') for x in re.split(r'(?<!\\)\|', lineas[i].strip().strip('|'))]
                if not all(re.fullmatch(r':?-+:?', x) for x in celdas):
                    filas.append(celdas)
                i += 1
            salida.append('<div class="tabla"><table>')
            for numero, fila in enumerate(filas):
                etiqueta = 'th' if numero == 0 else 'td'
                salida.append('<tr>' + ''.join(f'<{etiqueta}>{inline(c)}</{etiqueta}>' for c in fila) + '</tr>')
            salida.append('</table></div>')
            continue
        if linea.startswith('> '):
            citas = []
            while i < len(lineas) and lineas[i].startswith('> '):
                citas.append(lineas[i][2:])
                i += 1
            salida.append('<blockquote>' + inline(' '.join(citas)) + '</blockquote>')
            continue
        lista = re.match(r'^(- |\d+\. )(.+)', linea)
        if lista:
            ordenada = lista[1] != '- '
            etiqueta = 'ol' if ordenada else 'ul'
            salida.append(f'<{etiqueta}>')
            while i < len(lineas):
                elemento = re.match(r'^(\d+\. |\- )(.+)', lineas[i])
                if not elemento or (elemento[1] != '- ') != ordenada:
                    break
                salida.append('<li>' + inline(elemento[2]) + '</li>')
                i += 1
            salida.append(f'</{etiqueta}>')
            continue
        parrafo = [linea]
        i += 1
        while i < len(lineas) and lineas[i].strip() and not re.match(r'^(#|\||>|```|\- |\d+\. )', lineas[i]):
            parrafo.append(lineas[i])
            i += 1
        salida.append('<p>' + inline(' '.join(parrafo)) + '</p>')
    return '\n'.join(salida)


def generar():
    archivos = sorted(DOCS.glob('0[1-5]_*.md'))
    menu = ''.join(f'<a href="#guia-{i}">{escape(archivo.stem.replace("_", " "))}</a>' for i, archivo in enumerate(archivos, 1))
    contenido = ''.join(f'<section id="guia-{i}">{markdown(archivo.read_text(encoding="utf-8-sig"))}</section>' for i, archivo in enumerate(archivos, 1))
    html = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Guía de estudio · SistemaPedidos</title><style>
:root{font-family:Segoe UI,Arial,sans-serif;color:#24392e;background:#eef3ef}*{box-sizing:border-box}body{margin:0}header{background:#214e3b;color:white;padding:34px max(24px,calc((100% - 1020px)/2))}header h1{margin:0 0 10px}header p{margin:0;line-height:1.6;color:#e0ece3}nav,main{max-width:1060px;margin:24px auto;padding:0 20px}nav{display:flex;gap:10px;flex-wrap:wrap}nav a{background:white;border:1px solid #ceddd1;padding:10px 14px;border-radius:7px;font-weight:600}section{padding:30px 34px;background:white;border:1px solid #d9e5dc;border-radius:12px;margin:0 0 24px;scroll-margin-top:20px}h1{font-size:28px}h2{font-size:22px;margin-top:34px;color:#21553c}h3{font-size:18px;margin-top:26px}p,li{line-height:1.7}li{margin:7px 0}a{color:#176443;text-decoration:none}a:hover{text-decoration:underline}code{font-family:Consolas,monospace;background:#edf3ef;padding:2px 4px;border-radius:3px;font-size:.92em}pre{background:#edf3ef;border:1px solid #dce7df;padding:16px;border-radius:7px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.55}pre code{padding:0}.tabla{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px;margin:14px 0}th,td{border:1px solid #dce6df;text-align:left;padding:10px;vertical-align:top;line-height:1.5}th{background:#eaf2ed;color:#234c36}blockquote,.flujo{margin:20px 0;padding:18px 20px;background:#eff6f0;border-left:4px solid #4a8863;line-height:1.7}.nota{font-size:13px;color:#65766b}img{display:block;width:100%;height:auto;margin:20px auto}footer{max-width:1020px;margin:24px auto 40px;padding:0 20px;color:#62766a;font-size:13px}@media(max-width:600px){section{padding:20px}h1{font-size:24px}table{font-size:13px}}
@media print{@page{size:A4;margin:17mm}body{background:white;font-size:10pt}header{padding:0 0 16px;color:#214e3b;background:white;border-bottom:2px solid #214e3b}header p{color:#52665a}nav{display:none}main{padding:0;margin:0;max-width:none}section{border:0;border-radius:0;padding:0;margin:0;break-before:page}h1{font-size:22pt}h2{font-size:15pt;break-after:avoid}h3{font-size:12pt;break-after:avoid}tr,pre,blockquote{break-inside:avoid}table{font-size:9pt}a{color:inherit}footer{margin:16px 0;padding:0}img{max-height:220mm;object-fit:contain}}
</style></head><body><header><h1>SistemaPedidos · Guía de estudio</h1><p>Qué hace la app, cómo funciona el código, cómo se organiza la base y cómo defender el proyecto.<br>Documento local de lectura. Para imprimir o guardar en PDF: Ctrl+P.</p></header><nav>''' + menu + '</nav><main>' + contenido + '</main><footer>Material basado en el código del proyecto. No incluye registros de clientes, tokens ni comprobantes reales. Ver también INDICE_DEL_CODIGO.md y esquema_sqlite.sql.</footer></body></html>'
    destino = DOCS / 'GUIA_COMPLETA.html'
    destino.write_text(html, encoding='utf-8')
    print('Guía de lectura generada en docs/GUIA_COMPLETA.html')


if __name__ == '__main__':
    generar()
