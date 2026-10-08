from pydantic import BaseModel, Field, model_validator
from typing import Literal


class DetallePedidoCreate(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)


class PedidoCreate(BaseModel):
    cliente: str = Field(min_length=1, max_length=120)
    direccion: str = Field(min_length=1, max_length=250)
    telefono: str | None = Field(default=None, max_length=40)
    metodo_pago: str | None = Field(default=None, max_length=40)
    zona_entrega: Literal["microcentro"] | None = None
    monto_efectivo: float | None = Field(default=None, ge=0)
    comprobante_file_id: str | None = Field(default=None, max_length=255)
    comprobante_mime_type: str | None = Field(default=None, max_length=120)
    comprobante_nombre: str | None = Field(default=None, max_length=255)
    telegram_user_id: str | None = Field(default=None, max_length=40)
    detalles: list[DetallePedidoCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validar_datos_pago(self):
        if self.metodo_pago == "Efectivo" and self.monto_efectivo is None:
            raise ValueError("Falta indicar con cuánto pagará el cliente")
        if self.metodo_pago == "Transferencia" and not self.comprobante_file_id:
            raise ValueError("Falta el comprobante de transferencia")
        return self
