from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Date
from sqlalchemy.orm import relationship
from app.database import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    jornada_id = Column(Integer, ForeignKey("jornadas.id"), nullable=True, index=True)
    cliente = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    telegram_user_id = Column(String, nullable=True, index=True)
    total = Column(Float, nullable=False)
    estado = Column(String, nullable=False, default="pendiente")
    metodo_pago = Column(String, nullable=True)
    zona_entrega = Column(String, nullable=True)
    costo_envio = Column(Float, nullable=False, default=0)
    monto_efectivo = Column(Float, nullable=True)
    comprobante_file_id = Column(String, nullable=True)
    comprobante_mime_type = Column(String, nullable=True)
    comprobante_nombre = Column(String, nullable=True)
    pago_verificado = Column(Boolean, nullable=False, default=False)

    detalles = relationship(
        "DetallePedido",
        back_populates="pedido"
    )
    jornada = relationship("Jornada", back_populates="pedidos")


class Jornada(Base):
    __tablename__ = "jornadas"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, index=True)
    iniciada_en = Column(DateTime, nullable=False, default=datetime.now)
    cerrada_en = Column(DateTime, nullable=True)
    cantidad_pedidos = Column(Integer, nullable=False, default=0)
    total_ventas = Column(Float, nullable=False, default=0)

    pedidos = relationship("Pedido", back_populates="jornada")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

    detalles = relationship(
        "DetallePedido",
        back_populates="producto"
    )


class DetallePedido(Base):
    __tablename__ = "detalle_pedidos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio = Column(Float, nullable=False)

    pedido = relationship(
        "Pedido",
        back_populates="detalles"
    )

    producto = relationship(
        "Producto",
        back_populates="detalles"
    )


class UsuarioPanel(Base):
    __tablename__ = "usuarios_panel"

    id = Column(Integer, primary_key=True, index=True)
    nombre_usuario = Column(String(80), nullable=False, unique=True, index=True)
    rol = Column(String(20), nullable=False)
    sal_password = Column(String(64), nullable=False)
    hash_password = Column(String(128), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class SesionPanel(Base):
    __tablename__ = "sesiones_panel"

    token_hash = Column(String(64), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios_panel.id"), nullable=False, index=True)
    expira_en = Column(DateTime, nullable=False, index=True)

    usuario = relationship("UsuarioPanel")
