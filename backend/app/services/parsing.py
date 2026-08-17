"""
Parseo del reporte ReportePlantaProduccion de Sernapesca (.xls/.xlsx).

Port 1:1 de parseRows() / parseProducto() / speciesKey() en Codigo.gs.
Mismos índices de columna que el export de Sernapesca (0-indexado):

  2=N°Declaración, 4=Fecha Declaración, 11=Mat.Prima/Producto, 13=Tipo Ítem,
  14=Código Recurso/Producto, 15=Nombre, 17=Toneladas, 20=Lote, 21=Tipo Origen,
  22=Fecha Elaboración/Desembarque, 23=Elaborador/Agente Origen,
  24=N°Declaración Origen, 32=Nombre Bodega (columna AG del reporte Sernapesca)

Verificado contra un export real (ReportePlantaProduccion (Julio).xls,
agosto 2026) — los índices calzan exactamente.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from io import BytesIO

import pandas as pd


@dataclass
class ProductoPartes:
    especie: str = ""
    proceso_producto: str = ""
    tipo_frio: str = ""
    producto_global: str = ""
    preparacion: str = ""


@dataclass
class RawRow:
    row_num: int
    ndecl: str
    fecha_decl: dt.date | None
    matprod: str
    tipo_item: str
    codigo_producto: str
    nombre: str
    ton: float
    lote: str
    tipo_origen: str
    fecha_elab: dt.date | None
    agente: str
    ndecl_origen: str
    bodega: str
    species: str = field(default="")

    def __post_init__(self):
        if not self.species:
            self.species = species_key(self.nombre)


def to_date(v) -> dt.date | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, pd.Timestamp):
        return v.date()
    s = str(v).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def clean_str(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def clean_float(v) -> float:
    try:
        f = float(v)
        return 0.0 if pd.isna(f) else f
    except (TypeError, ValueError):
        return 0.0


def parse_producto(nombre: str | None) -> ProductoPartes:
    """
    Separa el nombre largo de producto en sus 5 componentes.
    Soporta tanto "A - B - C - D - E - ..." como "[A][B][C][D][E]...".
    """
    n = (nombre or "").strip()
    if n.startswith("["):
        parts = [p for p in n.replace("[", "|").replace("]", "|").split("|") if p != ""]
    else:
        parts = [p.strip() for p in n.split(" - ")]
    while len(parts) < 5:
        parts.append("")
    return ProductoPartes(
        especie=parts[0],
        proceso_producto=parts[1],
        tipo_frio=parts[2],
        producto_global=parts[3],
        preparacion=parts[4],
    )


def species_key(name: str | None) -> str:
    n = (name or "").strip()
    if n.startswith("["):
        n = n[1:].split("]")[0]
    else:
        n = n.split(" - ")[0]
    return n.strip().upper()


_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # .xls / .xlt legacy binario (BIFF)
_ZIP_MAGIC = b"PK\x03\x04"  # .xlsx / .xltx (OOXML, es un .zip)


def excel_engine_for(raw_bytes: bytes) -> str:
    """
    Sniffea la firma binaria en vez de confiar en la extensión del archivo —
    en la práctica llegan archivos ".xlt" que en realidad son binario legacy
    (BIFF, como un .xls), no el formato zip/OOXML que la extensión sugiere.
    """
    header = raw_bytes[:8]
    if header.startswith(_OLE2_MAGIC):
        return "xlrd"
    if header.startswith(_ZIP_MAGIC):
        return "openpyxl"
    # fallback: por extensión
    return "xlrd"


def parse_rows(raw_bytes: bytes, filename: str) -> list[RawRow]:
    """Equivalente a parseRows(data) — data ya es la hoja completa como matriz."""
    engine = excel_engine_for(raw_bytes)
    df = pd.read_excel(BytesIO(raw_bytes), header=None, engine=engine)
    data = df.values

    rows: list[RawRow] = []
    for r in range(2, len(data)):  # fila 0 y 1 son título/encabezado
        row = data[r]
        ndecl = clean_str(row[2])
        if not ndecl:
            continue
        rows.append(
            RawRow(
                row_num=r + 1,
                ndecl=ndecl,
                fecha_decl=to_date(row[4]),
                matprod=clean_str(row[11]),
                tipo_item=clean_str(row[13]),
                codigo_producto=clean_str(row[14]),
                nombre=clean_str(row[15]),
                ton=clean_float(row[17]),
                lote=clean_str(row[20]),
                tipo_origen=clean_str(row[21]),
                fecha_elab=to_date(row[22]),
                agente=clean_str(row[23]),
                ndecl_origen=clean_str(row[24]),
                bodega=clean_str(row[32]) if len(row) > 32 else "",
            )
        )
    return rows
