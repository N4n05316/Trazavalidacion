"""
Modelo relacional de Certus.

Espeja 1:1 el modelo de datos que hoy vive en las hojas de Google Sheets
(ver Codigo.gs), pero normalizado:

  Detalle completo          -> Linea            (tabla maestra, acumulativa)
  Historial de Casos        -> Caso              (uno por lote "a revisar")
  Historial de Ejecuciones  -> Ejecucion         (una por archivo procesado)
  Materia Prima Externa     -> MateriaPrimaExterna
  Productividad Diaria      -> ProductividadDiaria (upsert por fecha)
  Sin determinar            -> SinDeterminar     (ligado a la ejecución que lo generó)

La deduplicación que en Apps Script se hacía comparando claves fila a fila
(appendDedup) se reemplaza acá por UNIQUE constraints reales sobre las mismas
columnas clave.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """
    Fuerza a que las columnas Enum guarden el .value legible (ej. "Materia
    Prima (DI)") en vez del .name de Python (ej. "MATERIA_PRIMA_DI"), que es
    lo que SQLAlchemy persiste por defecto — evita divergencia entre lo que
    hay en la base y las comparaciones .value usadas en el resto del código
    (filtros, reportes, export a Excel).
    """
    return [e.value for e in enum_cls]


class TipoLinea(str, enum.Enum):
    MATERIA_PRIMA_DI = "Materia Prima (DI)"
    MATERIA_PRIMA_PROPIA = "Materia Prima (Producción Propia)"
    PRODUCTO = "Producto"
    DESECHO = "Desecho"


class EstadoLote(str, enum.Enum):
    OK_UN_DI = "OK - un solo DI"
    OK_PARCIAL_DEFINITIVO = "OK - mismo barco, DI parcial+definitivo"
    REVISAR = "REVISAR - DI de barcos distintos"
    # estados informativos (no participan en la clasificación, solo se muestran)
    NA_LINEA_CONSUMO = "N/A - línea de consumo"
    NA_LOTE_NO_DETERMINADO = "N/A - lote no determinado"
    NA_LOTE_NO_RESUELTO = "N/A - lote no resuelto en este archivo"
    NA = "N/A"


class EstadoRevision(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO_ERROR = "CONFIRMADO ERROR"
    FALSO_POSITIVO = "FALSO POSITIVO"


class TipoArchivo(str, enum.Enum):
    PRODUCCION = "ReportePlantaProduccion"
    TRAZABILIDAD_INTERNA = "Trazabilidad"


class Rol(str, enum.Enum):
    OPERADOR = "operador"
    ADMIN = "admin"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(Enum(Rol, native_enum=False, values_callable=_enum_values), default=Rol.OPERADOR)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArchivoProcesado(Base):
    """Registro de archivos ya ingeridos, para no reprocesar el mismo archivo dos veces."""

    __tablename__ = "archivos_procesados"
    __table_args__ = (UniqueConstraint("nombre_archivo", "hash_contenido", name="uq_archivo_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    nombre_archivo: Mapped[str] = mapped_column(String(500))
    hash_contenido: Mapped[str] = mapped_column(String(64))  # sha256
    tipo: Mapped[TipoArchivo] = mapped_column(Enum(TipoArchivo, native_enum=False, values_callable=_enum_values))
    procesado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    procesado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    ejecucion: Mapped["Ejecucion"] = relationship(back_populates="archivo", uselist=False)


class Ejecucion(Base):
    """Historial de Ejecuciones: una fila por corrida/archivo de producción procesado."""

    __tablename__ = "ejecuciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    archivo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("archivos_procesados.id"))
    fecha_ejecucion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    archivo_nombre: Mapped[str] = mapped_column(String(500))
    lotes_ok: Mapped[int] = mapped_column(Integer, default=0)
    lotes_ok_parcial: Mapped[int] = mapped_column(Integer, default=0)
    lotes_revisar: Mapped[int] = mapped_column(Integer, default=0)
    lotes_sin_determinar: Mapped[int] = mapped_column(Integer, default=0)

    archivo: Mapped[ArchivoProcesado] = relationship(back_populates="ejecucion")
    sin_determinar: Mapped[list["SinDeterminar"]] = relationship(back_populates="ejecucion")


class LineaCruda(Base):
    """
    Copia fiel de CADA fila del archivo original (ReportePlantaProduccion),
    sin fusionar ni resolver — una por fila de Excel. Existe porque el motor
    de resolución (build_lote_events) fusiona líneas de Mat.Prima que
    comparten un mismo DI antes de persistirlas en `lineas`, y en casos de
    producción propia sin DI en la misma declaración ni siquiera llega a
    registrar las líneas de producto/desecho — ninguno de los dos es fiel al
    folio tal cual fue declarado. El facsímil PDF (sección 8 del brief) se
    reconstruye desde acá, no desde `lineas`, precisamente para poder
    mostrar "así se declaró" con total independencia de lo que el algoritmo
    de validación haya logrado resolver.

    La deduplicación es por (n_declaracion, fila_original) — NO por archivo —
    porque los reportes de Sernapesca son acumulativos: un export de julio
    contiene de nuevo todas las filas de febrero en la misma posición. Sin
    esto, subir reportes de meses sucesivos duplica cada línea ya vista
    (mismo criterio que appendDedup()/detalleKey en Codigo.gs para `lineas`).
    """

    __tablename__ = "lineas_crudas"
    __table_args__ = (UniqueConstraint("n_declaracion", "fila_original", name="uq_linea_cruda_declaracion_fila"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    archivo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("archivos_procesados.id"), index=True)
    fila_original: Mapped[int] = mapped_column(Integer)

    n_declaracion: Mapped[str] = mapped_column(String(50), index=True)
    fecha_declaracion: Mapped[date | None] = mapped_column(Date, nullable=True)
    matprod: Mapped[str] = mapped_column(String(20))  # 'Mat.Prima' | 'Producción'
    tipo_item: Mapped[str] = mapped_column(String(20))  # 'Recurso' | 'Producto'
    codigo_producto: Mapped[str] = mapped_column(String(50), default="")
    nombre: Mapped[str] = mapped_column(Text)
    especie: Mapped[str] = mapped_column(String(200), default="")
    toneladas: Mapped[float] = mapped_column(Float)
    lote: Mapped[str] = mapped_column(String(100), default="")
    tipo_origen: Mapped[str] = mapped_column(String(20), default="")  # 'DI' | 'PLA' | 'BF'
    fecha_elaboracion: Mapped[date | None] = mapped_column(Date, nullable=True)
    agente: Mapped[str] = mapped_column(String(100), default="")
    declaracion_origen: Mapped[str] = mapped_column(String(50), default="")  # N° Declaración Origen (DI o producción propia)
    nombre_bodega: Mapped[str] = mapped_column(String(200), default="")


class Linea(Base):
    """
    Detalle completo: tabla maestra acumulativa. UNA fila por cada línea del
    folio (materia prima DI, materia prima de producción propia, producto y
    desecho) — igual que 'rawLines' en buildLoteEvents().

    La clave de deduplicación replica appendDedup()/detalleKey en Codigo.gs:
    n_declaracion + lote + tipo_linea + codigo_producto + fila_original.
    """

    __tablename__ = "lineas"
    __table_args__ = (
        UniqueConstraint(
            "n_declaracion", "lote", "tipo_linea", "codigo_producto", "fila_original",
            name="uq_linea_dedup_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)

    lote: Mapped[str] = mapped_column(String(100), index=True, default="")
    tipo_linea: Mapped[TipoLinea] = mapped_column(Enum(TipoLinea, native_enum=False, values_callable=_enum_values))
    estado: Mapped[EstadoLote] = mapped_column(Enum(EstadoLote, native_enum=False, values_callable=_enum_values))

    n_declaracion: Mapped[str] = mapped_column(String(50), index=True)
    di: Mapped[str] = mapped_column(String(50), index=True, default="")
    declaracion_origen: Mapped[str] = mapped_column(String(50), default="")  # si es producción propia
    agente: Mapped[str] = mapped_column(String(100), default="")  # código de barco

    fecha_desembarque_di: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_elaboracion_linea: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_declaracion: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    producto: Mapped[str] = mapped_column(Text)  # nombre completo original
    especie: Mapped[str] = mapped_column(String(200), index=True)
    proceso_producto: Mapped[str] = mapped_column(String(200), default="")
    tipo_frio: Mapped[str] = mapped_column(String(200), default="")
    producto_global: Mapped[str] = mapped_column(String(200), default="")
    preparacion: Mapped[str] = mapped_column(String(300), default="")

    codigo_producto: Mapped[str] = mapped_column(String(50), default="")
    nombre_bodega: Mapped[str] = mapped_column(String(200), default="")
    toneladas: Mapped[float] = mapped_column(Float)
    fila_original: Mapped[int] = mapped_column(Integer)
    archivo_origen: Mapped[str] = mapped_column(String(500))

    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Caso(Base):
    """
    Historial de Casos: cada lote 'a revisar' queda registrado UNA vez
    (igual que en Codigo.gs — no se vuelve a tocar si ya existe, para
    preservar las anotaciones manuales de revisión).
    """

    __tablename__ = "casos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    lote: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    fecha_detectado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    di_asociados: Mapped[str] = mapped_column(String(300))  # CSV de DIs, como en la hoja original
    agentes: Mapped[str] = mapped_column(String(300))  # CSV de agentes/barcos
    n_declaraciones: Mapped[int] = mapped_column(Integer)
    estado_revision: Mapped[EstadoRevision] = mapped_column(
        Enum(EstadoRevision, native_enum=False, values_callable=_enum_values), default=EstadoRevision.PENDIENTE
    )
    notas: Mapped[str] = mapped_column(Text, default="")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    actualizado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class SinDeterminar(Base):
    """
    Sin determinar: casos donde el balance de toneladas no calzó dentro de
    la tolerancia para ninguna combinación de DI. A diferencia de Linea/Caso,
    esta tabla NO es acumulativa fila-a-fila global — se guarda por ejecución,
    ya que refleja el chequeo del archivo actual (igual que sh.clear() en
    writeUnresolvedSheet).
    """

    __tablename__ = "sin_determinar"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ejecucion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ejecuciones.id"))
    n_declaracion: Mapped[str] = mapped_column(String(50))
    especie: Mapped[str] = mapped_column(String(200))
    fecha_declaracion: Mapped[date | None] = mapped_column(Date, nullable=True)
    di_toneladas: Mapped[str] = mapped_column(Text)  # texto legible, igual que diTon.join('; ')
    out_toneladas: Mapped[str] = mapped_column(Text)  # texto legible, igual que outTon.join('; ')

    ejecucion: Mapped[Ejecucion] = relationship(back_populates="sin_determinar")


class MateriaPrimaExterna(Base):
    """
    Registro interno de la planta (Lote-DI), fuente independiente para el
    cruce de 3 vías. Viene del archivo 'Trazabilidad...xlsx', hoja
    'MATERIA PRIMA': columna C = lote interno, columna F = DI.
    """

    __tablename__ = "materia_prima_externa"
    __table_args__ = (
        UniqueConstraint("lote_interno", "di_externo", "especie", name="uq_mp_externa_dedup_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    lote_interno: Mapped[str] = mapped_column(String(100), index=True)
    di_externo: Mapped[str] = mapped_column(String(100), index=True)
    barco: Mapped[str] = mapped_column(String(100), default="")
    especie: Mapped[str] = mapped_column(String(200), default="")
    fecha_recalada: Mapped[date | None] = mapped_column(Date, nullable=True)
    archivo_origen: Mapped[str] = mapped_column(String(500))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ProductividadDiaria(Base):
    """Productividad Diaria: una fila por fecha de declaración, se reescribe (upsert) cada corrida."""

    __tablename__ = "productividad_diaria"

    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    n_declaraciones: Mapped[int] = mapped_column(Integer)
    n_lineas_totales: Mapped[int] = mapped_column(Integer)
    n_lineas_materia_prima: Mapped[int] = mapped_column(Integer)
    n_lineas_produccion: Mapped[int] = mapped_column(Integer)
    n_di_distintos: Mapped[int] = mapped_column(Integer)
    n_especies_distintas: Mapped[int] = mapped_column(Integer)
    toneladas_producto: Mapped[float] = mapped_column(Float)
    toneladas_materia_prima: Mapped[float] = mapped_column(Float)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
