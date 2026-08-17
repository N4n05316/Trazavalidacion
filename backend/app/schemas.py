from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict

from app.models import EstadoRevision, Rol


class LoginRequest(BaseModel):
    email: str
    password: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nombre: str
    rol: Rol
    activo: bool
    creado_en: dt.datetime
    ultimo_login: dt.datetime | None


class UsuarioCreate(BaseModel):
    email: str
    nombre: str
    password: str
    rol: Rol = Rol.OPERADOR


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    rol: Rol | None = None
    activo: bool | None = None
    password: str | None = None


class EjecucionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fecha_ejecucion: dt.datetime
    archivo_nombre: str
    lotes_ok: int
    lotes_ok_parcial: int
    lotes_revisar: int
    lotes_sin_determinar: int


class CasoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lote: str
    fecha_detectado: dt.datetime
    di_asociados: str
    agentes: str
    n_declaraciones: int
    estado_revision: EstadoRevision
    notas: str


class CasoUpdate(BaseModel):
    estado_revision: EstadoRevision | None = None
    notas: str | None = None


class LineaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lote: str
    tipo_linea: str
    estado: str
    n_declaracion: str
    di: str
    declaracion_origen: str
    agente: str
    fecha_desembarque_di: dt.date | None
    fecha_elaboracion_linea: dt.date | None
    fecha_declaracion: dt.date | None
    producto: str
    especie: str
    codigo_producto: str
    nombre_bodega: str
    toneladas: float
    archivo_origen: str


class BalanceMasaOut(BaseModel):
    n_declaracion: str
    di: str
    lote: str
    especie: str
    materia_prima_ton: float
    producto_ton: float
    desecho_ton: float
    balance: float  # materia_prima - (producto + desecho)


class ProductividadDiariaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: dt.date
    n_declaraciones: int
    n_lineas_totales: int
    n_lineas_materia_prima: int
    n_lineas_produccion: int
    n_di_distintos: int
    n_especies_distintas: int
    toneladas_producto: float
    toneladas_materia_prima: float


class CruceLoteDiOut(BaseModel):
    lote: str
    di_externo: list[str]
    di_resuelto: list[str]
    estado_cruce: str
    estado_interno: str
    especies: list[str]
    barcos: list[str]
    fecha: dt.date | None


class IngestResult(BaseModel):
    ejecucion: EjecucionOut
    lotes_ok: int
    lotes_ok_parcial: int
    lotes_revisar: int
    lotes_sin_determinar: int
