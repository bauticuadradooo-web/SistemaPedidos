"""Pruebas aisladas: no leen la base real ni envían mensajes a clientes."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

TEMP = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(TEMP.name) / 'pruebas.db').as_posix()
os.environ['TELEGRAM_BOT_TOKEN'] = ''
os.environ['PANEL_COOKIE_SECURE'] = 'false'

from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Pedido, Producto, Jornada, DetallePedido, EventoPedido, MovimientoStock
from app.services.cambios import cancelar_por_cliente, cancelar_parcial
from app.services.pedidos import crear_pedido
from app.schemas import PedidoCreate
from app.services.telegram import enviar_evento
from app import telegram_bot


class CambiosTest(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.client = TestClient(app)
        credenciales = {rol: {'nombre_usuario': rol, 'password': 'PruebaSegura123!'}
                        for rol in ('administrador', 'preparador', 'despachante')}
        self.assertEqual(self.client.post('/auth/setup', json=credenciales).status_code, 201)
        with SessionLocal() as db:
            db.add(Jornada(fecha=date.today()))
            db.add_all([Producto(nombre='Férnet', precio=1000, stock=10), Producto(nombre='Coca', precio=500, stock=10)])
            db.commit()
        self.pedido = self.nuevo_pedido()

    def nuevo_pedido(self, transferencia=False):
        with SessionLocal() as db:
            pedido = crear_pedido(db, PedidoCreate(cliente='Prueba', direccion='Mitre 100',
                telegram_user_id='123', metodo_pago='Transferencia' if transferencia else 'Coordinar',
                comprobante_file_id='fake' if transferencia else None,
                detalles=[{'producto_id': 1, 'cantidad': 3}, {'producto_id': 2, 'cantidad': 2}]))
            return pedido.id

    def login(self, rol):
        self.assertEqual(self.client.post('/auth/login', json={'nombre_usuario': rol, 'password': 'PruebaSegura123!'}).status_code, 200)

    def detalle(self, pedido_id=None):
        with SessionLocal() as db:
            return db.query(DetallePedido).filter_by(pedido_id=pedido_id or self.pedido, producto_id=1).first().id

    def parcial(self, **overrides):
        datos = {'detalle_id': overrides.get('detalle_id') or self.detalle(), 'cantidad': 1, 'motivo': 'Rotura: botella dañada', 'reponer_stock': False}
        datos.update(overrides)
        return self.client.post(f'/pedidos/{self.pedido}/cancelacion-parcial', json=datos)

    def test_preparador_baja_y_busqueda(self):
        self.login('preparador')
        encontrados = self.client.get('/productos?q=fernet').json()
        self.assertEqual([p['id'] for p in encontrados], [1])
        self.assertNotIn('precio', encontrados[0])
        r = self.client.patch('/productos/1/stock', json={'delta': -2, 'motivo': 'Vencimiento de unidades', 'pedido_id': self.pedido})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['stock'], 5)
        with SessionLocal() as db:
            self.assertEqual(db.query(MovimientoStock).count(), 1)
            self.assertEqual(db.query(EventoPedido).count(), 1)
            self.assertEqual(db.get(Pedido, self.pedido).total, 5500)

    def test_limites_y_roles_stock(self):
        self.login('preparador')
        for datos, codigo in [({'delta': 1, 'motivo': 'Ingreso'}, 403),
                              ({'delta': -100, 'motivo': 'Faltantes'}, 422),
                              ({'delta': -1, 'motivo': '   '}, 422),
                              ({'delta': -1}, 422)]:
            self.assertEqual(self.client.patch('/productos/1/stock', json=datos).status_code, codigo)
        self.login('despachante')
        self.assertEqual(self.client.get('/productos').status_code, 403)
        self.assertEqual(self.parcial().status_code, 403)

    def test_parcial_perdida_sin_doble_descuento(self):
        self.login('preparador')
        self.assertEqual(self.parcial().status_code, 200)
        with SessionLocal() as db:
            self.assertEqual(db.get(Producto, 1).stock, 7)
            self.assertEqual(db.get(Pedido, self.pedido).total, 4500)
            self.assertEqual(db.get(Pedido, self.pedido).estado, 'pendiente')
        # Cancelar luego devuelve solo las unidades restantes.
        with SessionLocal() as db:
            cancelar_por_cliente(db, self.pedido, '123')
        with SessionLocal() as db:
            self.assertEqual(db.get(Producto, 1).stock, 9)
            self.assertEqual(db.get(Producto, 2).stock, 10)

    def test_parcial_reposicion_y_linea_completa(self):
        self.assertEqual(self.parcial(cantidad=3, reponer_stock=True).status_code, 200)
        with SessionLocal() as db:
            pedido = db.get(Pedido, self.pedido)
            self.assertEqual(pedido.total, 2500)
            self.assertEqual(db.get(Producto, 1).stock, 10)
            self.assertEqual(len(pedido.detalles), 1)
        linea = self.client.get(f'/pedidos/{self.pedido}').json()['detalles'][0]
        self.assertEqual(self.parcial(detalle_id=linea['detalle_id'], cantidad=2).status_code, 409)

    def test_parcial_validacion_pertenencia_y_archivo(self):
        otro = self.nuevo_pedido()
        self.assertEqual(self.parcial(detalle_id=self.detalle(otro)).status_code, 422)
        self.assertEqual(self.parcial(cantidad=99).status_code, 422)
        self.assertEqual(self.parcial(motivo='   ').status_code, 422)
        with SessionLocal() as db:
            db.get(Jornada, db.get(Pedido, self.pedido).jornada_id).cerrada_en = datetime.now()
            db.commit()
        self.assertEqual(self.parcial().status_code, 409)

    def test_parcial_transferencia_registra_reintegro(self):
        self.pedido = self.nuevo_pedido(transferencia=True)
        self.assertEqual(self.parcial().status_code, 200)
        eventos = self.client.get(f'/pedidos/{self.pedido}').json()['eventos']
        self.assertIn('Importe a reintegrar', eventos[0]['descripcion'])
        self.assertFalse(eventos[0]['notificado'])

    def test_delivery_motivo_y_roles(self):
        self.login('despachante')
        url = f'/pedidos/{self.pedido}/incidencias-delivery'
        self.assertEqual(self.client.post(url, json={'motivo': 'Pinchadura: demora de 20 minutos'}).status_code, 409)
        with SessionLocal() as db:
            db.get(Pedido, self.pedido).estado = 'en_camino'
            db.commit()
        self.assertEqual(self.client.post(url, json={'motivo': 'Pinchadura: demora de 20 minutos'}).status_code, 200)
        self.assertEqual(self.client.post(url, json={'motivo': '   '}).status_code, 422)
        with SessionLocal() as db:
            self.assertEqual(db.get(Pedido, self.pedido).estado, 'en_camino')
        self.login('preparador')
        self.assertEqual(self.client.post(url, json={'motivo': 'Resuelto'}).status_code, 403)

    def test_cliente_propietario_solo_pendiente(self):
        with SessionLocal() as db:
            with self.assertRaises(HTTPException) as error:
                cancelar_por_cliente(db, self.pedido, '999')
            self.assertEqual(error.exception.status_code, 404)
        with SessionLocal() as db:
            cancelar_por_cliente(db, self.pedido, '123')
        with SessionLocal() as db:
            self.assertEqual(db.get(Producto, 1).stock, 10)
            with self.assertRaises(HTTPException):
                cancelar_por_cliente(db, self.pedido, '123')
        with SessionLocal() as db:
            self.assertEqual(db.get(Producto, 1).stock, 10)

    def test_preparacion_bloquea_cancelacion_y_retroceso(self):
        self.login('preparador')
        self.assertEqual(self.client.put(f'/pedidos/{self.pedido}/estado?nuevo_estado=preparando').status_code, 200)
        with SessionLocal() as db:
            with self.assertRaises(HTTPException):
                cancelar_por_cliente(db, self.pedido, '123')
        self.login('administrador')
        self.assertEqual(self.client.put(f'/pedidos/{self.pedido}/estado?nuevo_estado=pendiente').status_code, 409)
        self.assertEqual(self.client.put(f'/pedidos/{self.pedido}/estado?nuevo_estado=entregado').status_code, 409)

    def test_cancelacion_concurrente_no_duplica_stock(self):
        def cancelar():
            try:
                with SessionLocal() as db:
                    cancelar_por_cliente(db, self.pedido, '123')
                return 200
            except HTTPException as error:
                return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = sorted(pool.map(lambda _: cancelar(), range(2)))
        self.assertEqual(resultados, [200, 409])
        with SessionLocal() as db:
            self.assertEqual(db.get(Producto, 1).stock, 10)

    def test_telegram_reintento_y_confirmacion(self):
        self.assertEqual(self.parcial().status_code, 200)
        with SessionLocal() as db:
            evento_id = db.query(EventoPedido).first().id
        with patch.dict(os.environ, TELEGRAM_BOT_TOKEN='token-falso'), patch('app.services.telegram.httpx.post') as post:
            post.return_value.json.return_value = {'ok': False}
            self.assertFalse(enviar_evento(evento_id))
            post.return_value.json.return_value = {'ok': True}
            self.assertTrue(enviar_evento(evento_id))
            self.assertTrue(enviar_evento(evento_id))
            self.assertEqual(post.call_count, 2)
            self.assertEqual(post.call_args.kwargs['json']['chat_id'], '123')
            self.assertIn('Rotura', post.call_args.kwargs['json']['text'])

    def test_bot_confirmacion_revalida_estado(self):
        query = SimpleNamespace(data=f'anular:consultar:{self.pedido}', answer=AsyncMock(), edit_message_text=AsyncMock())
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=123))
        asyncio.run(telegram_bot.cancelar_pedido_callback(update, SimpleNamespace()))
        self.assertIn('Confirmás', query.edit_message_text.call_args.args[0])
        with SessionLocal() as db:
            db.get(Pedido, self.pedido).estado = 'preparando'
            db.commit()
        query.data = f'anular:confirmar:{self.pedido}'
        asyncio.run(telegram_bot.cancelar_pedido_callback(update, SimpleNamespace()))
        self.assertIn('Solo podés cancelar', query.edit_message_text.call_args.args[0])
        with SessionLocal() as db:
            self.assertEqual(db.get(Pedido, self.pedido).estado, 'preparando')


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        engine.dispose()
        TEMP.cleanup()
