import base64
import binascii
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.auth import exigir_roles, obtener_db
from app.models import DevolucionPedido, EventoPedido, Pedido
from app.services.cambios import iniciar_escritura
from app.services.devoluciones import cancelado_por_cliente, enviar_comprobante_devolucion

router = APIRouter(prefix='/devoluciones', tags=['devoluciones'])
MAX_ARCHIVO = 5 * 1024 * 1024


class DevolucionRegistrar(BaseModel):
    alias_destino: str = Field(min_length=3, max_length=80)
    importe: Decimal = Field(gt=0, le=Decimal('999999999999.99'), max_digits=14, decimal_places=2)
    archivo_base64: str = Field(min_length=4, max_length=7 * 1024 * 1024)
    mime_type: Literal['application/pdf', 'image/jpeg', 'image/png']
    origen_verificado: Literal[True]
    transferencia_realizada: Literal[True]


async def leer_datos(request: Request):
    contenido = bytearray()
    async for fragmento in request.stream():
        contenido.extend(fragmento)
        if len(contenido) > 7 * 1024 * 1024 + 4096:
            raise HTTPException(413, 'El comprobante debe pesar como máximo 5 MB')
    try:
        return DevolucionRegistrar.model_validate_json(contenido)
    except ValidationError:
        raise HTTPException(422, 'Revisá el importe, el archivo y las confirmaciones de pago y cuenta de origen')


@router.get('')
def listar(db: Session = Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))):
    # Incluye jornadas archivadas: cerrar un día no debe esconder una devolución.
    pedidos = db.query(Pedido).filter(Pedido.estado == 'cancelado', Pedido.metodo_pago == 'Transferencia',
        Pedido.comprobante_file_id.is_not(None), Pedido.id.in_(db.query(EventoPedido.pedido_id).filter_by(tipo='cancelacion_cliente'))).order_by(Pedido.id.desc()).all()
    resultado = []
    for pedido in pedidos:
        registro = db.query(DevolucionPedido).filter_by(pedido_id=pedido.id).first()
        parcial = bool(db.query(EventoPedido.id).filter_by(pedido_id=pedido.id, tipo='cancelacion_parcial').first())
        resultado.append({'pedido_id': pedido.id, 'cliente': pedido.cliente, 'alias_cliente': pedido.alias_cliente,
            'importe_sugerido': pedido.total, 'pago_verificado': pedido.pago_verificado,
            'parcial_previa': parcial, 'telegram_disponible': bool(pedido.telegram_user_id),
            'devolucion': None if not registro else {'id': registro.id, 'alias_destino': registro.alias_destino,
                'importe': float(registro.importe), 'enviado_telegram': registro.enviado_telegram,
                'autor': registro.autor, 'fecha': registro.creado_en.isoformat() + 'Z'}})
    return resultado


@router.post('/pedidos/{pedido_id}')
def registrar(pedido_id: int, background_tasks: BackgroundTasks,
              _usuario=Depends(exigir_roles('administrador')),
              datos: DevolucionRegistrar = Depends(leer_datos), db: Session = Depends(obtener_db)):
    iniciar_escritura(db)
    pedido = db.query(Pedido).filter_by(id=pedido_id).with_for_update().first()
    if not pedido or not cancelado_por_cliente(db, pedido):
        raise HTTPException(409, 'La devolución requiere un pedido con comprobante de transferencia cancelado por el cliente')
    if db.query(DevolucionPedido.id).filter_by(pedido_id=pedido.id).first():
        raise HTTPException(409, 'Esta devolución ya se registró. Usá Reintentar envío para reenviar el mismo comprobante')
    if not pedido.alias_cliente or datos.alias_destino != pedido.alias_cliente:
        raise HTTPException(409, 'El alias debe coincidir con el informado por el cliente. Actualizá la página y revisá la cuenta de origen del pago')
    try:
        archivo = base64.b64decode(datos.archivo_base64, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, 'El archivo no es válido')
    if not archivo or len(archivo) > MAX_ARCHIVO:
        raise HTTPException(413, 'El comprobante debe pesar entre 1 byte y 5 MB')
    firmas = {'application/pdf': (b'%PDF-', '.pdf'), 'image/jpeg': (b'\xff\xd8\xff', '.jpg'), 'image/png': (b'\x89PNG\r\n\x1a\n', '.png')}
    firma, extension = firmas[datos.mime_type]
    if not archivo.startswith(firma):
        raise HTTPException(422, 'El contenido del comprobante no corresponde a un PDF, JPG o PNG válido')
    registro = DevolucionPedido(pedido_id=pedido.id, alias_destino=pedido.alias_cliente,
        importe=datos.importe, comprobante=archivo, mime_type=datos.mime_type,
        nombre_archivo=f'devolucion-pedido-{pedido.id}{extension}', autor=_usuario.nombre_usuario)
    pedido.pago_verificado = True  # El administrador confirma que revisó el ingreso original.
    db.add(registro)
    db.commit()
    background_tasks.add_task(enviar_comprobante_devolucion, registro.id)
    return {'mensaje': 'Devolución registrada. El comprobante se enviará por Telegram; consultá el estado del envío.', 'id': registro.id}


@router.get('/{devolucion_id}/comprobante')
def comprobante(devolucion_id: int, db: Session = Depends(obtener_db), _usuario=Depends(exigir_roles('administrador'))):
    registro = db.get(DevolucionPedido, devolucion_id)
    if not registro:
        raise HTTPException(404, 'Devolución no encontrada')
    return Response(registro.comprobante, media_type=registro.mime_type,
        headers={'Content-Disposition': f'attachment; filename="{registro.nombre_archivo}"',
                 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.post('/{devolucion_id}/reenviar')
def reenviar(devolucion_id: int, background_tasks: BackgroundTasks, db: Session = Depends(obtener_db),
             _usuario=Depends(exigir_roles('administrador'))):
    if not db.get(DevolucionPedido, devolucion_id):
        raise HTTPException(404, 'Devolución no encontrada')
    background_tasks.add_task(enviar_comprobante_devolucion, devolucion_id)
    return {'mensaje': 'Reintento solicitado. No se registra otra devolución ni se transfiere dinero de nuevo.'}
