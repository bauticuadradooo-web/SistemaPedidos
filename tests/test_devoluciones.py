import asyncio
import atexit
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tests import test_cambios as fixture
atexit.register(fixture.engine.dispose)
from fastapi import HTTPException
from app.database import SessionLocal
from app.models import DevolucionPedido, EventoPedido, Jornada, Pedido
from app.services.cambios import cancelar_por_cliente
from app.services.devoluciones import guardar_alias_cliente, enviar_comprobante_devolucion
from app import telegram_bot


class DevolucionesTest(unittest.TestCase):
    nuevo_pedido = fixture.CambiosTest.nuevo_pedido
    login = fixture.CambiosTest.login

    def setUp(self):
        fixture.CambiosTest.setUp(self)
        self.pedido = self.nuevo_pedido(transferencia=True)
        with SessionLocal() as db:
            guardar_alias_cliente(db, self.pedido, '123', 'cliente.cuenta')
        with SessionLocal() as db:
            cancelar_por_cliente(db, self.pedido, '123')

    def datos(self, **overrides):
        datos = {'alias_destino': 'cliente.cuenta', 'importe': '5500.00',
                 'archivo_base64': base64.b64encode(b'%PDF-1.4\nComprobante ficticio\n%%EOF').decode(),
                 'mime_type': 'application/pdf', 'origen_verificado': True, 'transferencia_realizada': True}
        datos.update(overrides)
        return datos

    def registrar(self, **overrides):
        return self.client.post(f'/devoluciones/pedidos/{self.pedido}', json=self.datos(**overrides))

    def test_aparece_automaticamente_y_persiste_al_archivar(self):
        filas = self.client.get('/devoluciones').json()
        self.assertEqual([p['pedido_id'] for p in filas], [self.pedido])
        self.assertEqual(filas[0]['alias_cliente'], 'cliente.cuenta')
        self.assertIsNone(filas[0]['devolucion'])
        with SessionLocal() as db:
            db.get(Jornada, db.get(Pedido, self.pedido).jornada_id).cerrada_en = datetime.now()
            db.commit()
        self.assertEqual(len(self.client.get('/devoluciones').json()), 1)
        self.assertEqual(self.registrar().status_code, 200)

    def test_guarda_recibo_y_no_duplica(self):
        r = self.registrar()
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.registrar().status_code, 409)
        fila = self.client.get('/devoluciones').json()[0]
        self.assertFalse(fila['devolucion']['enviado_telegram'])
        recibo = self.client.get(f"/devoluciones/{r.json()['id']}/comprobante")
        self.assertEqual(recibo.status_code, 200)
        self.assertEqual(recibo.headers['content-type'], 'application/pdf')
        self.assertTrue(recibo.content.startswith(b'%PDF-'))
        self.assertNotIn('archivo_base64', fila['devolucion'])
        with SessionLocal() as db:
            self.assertEqual(db.query(DevolucionPedido).count(), 1)
            self.assertTrue(db.get(Pedido, self.pedido).pago_verificado)

    def test_permisos_y_recibo_protegido(self):
        registro_id = self.registrar().json()['id']
        for rol in ('preparador', 'despachante'):
            self.login(rol)
            self.assertEqual(self.client.get('/devoluciones').status_code, 403)
            self.assertEqual(self.registrar().status_code, 403)
            self.assertEqual(self.client.get(f'/devoluciones/{registro_id}/comprobante').status_code, 403)
            self.assertEqual(self.client.post(f'/devoluciones/{registro_id}/reenviar').status_code, 403)

    def test_formato_tamano_e_importe(self):
        for cambio, codigo in [({'alias_destino': 'otra.cuenta'}, 409),
                               ({'importe': '0'}, 422), ({'importe': '-1'}, 422),
                               ({'importe': 'NaN'}, 422), ({'importe': '12.123'}, 422),
                               ({'transferencia_realizada': False}, 422), ({'origen_verificado': False}, 422),
                               ({'archivo_base64': '!!!!'}, 422),
                               ({'archivo_base64': base64.b64encode(b'<html>falso</html>').decode()}, 422),
                               ({'mime_type': 'text/html'}, 422)]:
            with self.subTest(cambio=list(cambio)):
                self.assertEqual(self.registrar(**cambio).status_code, codigo)
        grande = base64.b64encode(b'%PDF-' + b'x' * (5 * 1024 * 1024)).decode()
        self.assertEqual(self.registrar(archivo_base64=grande).status_code, 413)
        with SessionLocal() as db:
            self.assertEqual(db.query(DevolucionPedido).count(), 0)

    def test_sin_alias_y_cancelacion_no_del_cliente(self):
        with SessionLocal() as db:
            db.get(Pedido, self.pedido).alias_cliente = None
            db.commit()
        self.assertEqual(self.registrar().status_code, 409)
        with SessionLocal() as db:
            db.query(EventoPedido).filter_by(pedido_id=self.pedido, tipo='cancelacion_cliente').delete()
            db.commit()
        self.assertEqual(self.client.get('/devoluciones').json(), [])
        self.assertEqual(self.registrar().status_code, 409)

    def test_alias_solo_propietario_e_inmutable_tras_registro(self):
        with SessionLocal() as db:
            with self.assertRaises(HTTPException) as error:
                guardar_alias_cliente(db, self.pedido, '999', 'cuenta.falsa')
            self.assertEqual(error.exception.status_code, 404)
        with SessionLocal() as db:
            guardar_alias_cliente(db, self.pedido, '123', 'cuenta.nueva')
        self.assertEqual(self.registrar().status_code, 409)  # Formulario anterior queda obsoleto.
        self.assertEqual(self.registrar(alias_destino='cuenta.nueva').status_code, 200)
        with SessionLocal() as db:
            with self.assertRaises(HTTPException):
                guardar_alias_cliente(db, self.pedido, '123', 'otra.cuenta')

    def test_envio_archivo_correcto_y_reintento_sin_nueva_devolucion(self):
        registro_id = self.registrar().json()['id']
        with patch.dict(os.environ, TELEGRAM_BOT_TOKEN='token-falso'), patch('app.services.devoluciones.httpx.post') as post:
            post.return_value.json.return_value = {'ok': False}
            self.assertFalse(enviar_comprobante_devolucion(registro_id))
            post.return_value.json.return_value = {'ok': True}
            self.assertTrue(enviar_comprobante_devolucion(registro_id))
            self.assertTrue(enviar_comprobante_devolucion(registro_id))
            self.assertEqual(post.call_count, 2)
            self.assertEqual(post.call_args.kwargs['data']['chat_id'], '123')
            self.assertIn('cliente.cuenta', post.call_args.kwargs['data']['caption'])
            self.assertEqual(post.call_args.kwargs['files']['document'][0], f'devolucion-pedido-{self.pedido}.pdf')
            self.assertTrue(post.call_args.kwargs['files']['document'][1].startswith(b'%PDF-'))
        with SessionLocal() as db:
            self.assertTrue(db.get(DevolucionPedido, registro_id).enviado_telegram)
            self.assertEqual(db.query(DevolucionPedido).count(), 1)

    def test_no_reclama_envio_en_curso_y_recupera_abandonado(self):
        registro_id = self.registrar().json()['id']
        with SessionLocal() as db:
            db.get(DevolucionPedido, registro_id).envio_iniciado_en = datetime.utcnow()
            db.commit()
        with patch.dict(os.environ, TELEGRAM_BOT_TOKEN='token-falso'), patch('app.services.devoluciones.httpx.post') as post:
            self.assertFalse(enviar_comprobante_devolucion(registro_id))
            post.assert_not_called()
            with SessionLocal() as db:
                db.get(DevolucionPedido, registro_id).envio_iniciado_en = datetime.utcnow() - timedelta(minutes=3)
                db.commit()
            post.return_value.json.return_value = {'ok': True}
            self.assertTrue(enviar_comprobante_devolucion(registro_id))

    def test_bot_guarda_cuenta_para_pedido_anterior(self):
        mensaje = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_user=SimpleNamespace(id=123), effective_message=mensaje)
        context = SimpleNamespace(args=[str(self.pedido), 'alias.corregido'])
        asyncio.run(telegram_bot.alias_devolucion_cmd(update, context))
        self.assertIn('Guardamos la cuenta', mensaje.reply_text.call_args.args[0])
        with SessionLocal() as db:
            self.assertEqual(db.get(Pedido, self.pedido).alias_cliente, 'alias.corregido')

    def test_bot_pide_alias_antes_del_comprobante(self):
        mensaje = SimpleNamespace(text='cliente.cuenta', reply_text=AsyncMock())
        contexto = SimpleNamespace(user_data={'pedido': {}})
        estado = asyncio.run(telegram_bot.recibir_alias_transferencia(SimpleNamespace(effective_message=mensaje), contexto))
        self.assertEqual(estado, telegram_bot.COMPROBANTE)
        self.assertEqual(contexto.user_data['pedido']['alias_cliente'], 'cliente.cuenta')

    def test_dos_registros_concurrentes_guardan_un_solo_recibo(self):
        from app.routers.devoluciones import DevolucionRegistrar, registrar
        from fastapi import BackgroundTasks
        def guardar():
            try:
                with SessionLocal() as db:
                    registrar(self.pedido, BackgroundTasks(), SimpleNamespace(nombre_usuario='administrador'),
                              DevolucionRegistrar(**self.datos()), db)
                return 200
            except HTTPException as error:
                return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _: guardar(), range(2))), [200, 409])
        with SessionLocal() as db:
            self.assertEqual(db.query(DevolucionPedido).count(), 1)

    def test_migracion_agrega_alias_sin_perder_pedidos(self):
        import importlib
        import app.main as modulo_main
        from sqlalchemy import inspect, text
        with fixture.engine.begin() as connection:
            connection.execute(text('ALTER TABLE pedidos DROP COLUMN alias_cliente'))
        importlib.reload(modulo_main)
        self.assertIn('alias_cliente', {c['name'] for c in inspect(fixture.engine).get_columns('pedidos')})
        with SessionLocal() as db:
            self.assertEqual(db.get(Pedido, self.pedido).cliente, 'Prueba')


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        fixture.engine.dispose()
        fixture.TEMP.cleanup()

