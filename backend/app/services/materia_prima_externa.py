"""
Ingesta del archivo interno de la planta ("Trazabilidad...xlsx"), hoja
"MATERIA PRIMA": registro independiente de Lote interno <-> DI.

Port 1:1 de procesarTrazabilidadExterna() / writeMateriaPrimaExterna() en
Codigo.gs. Columnas esperadas (0-indexado): C(2)=Lote interno (Guía MMPP),
F(5)=N° DI, E(4)=Barco, G(6)=Fecha Recalada, H(7)=Especie.
Verificado contra un export real ("Trazabilidad 2026.xlt", hoja
"materia prima") — los índices calzan exactamente.
"""
from __future__ import annotations

import hashlib
import uuid
from io import BytesIO

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import ArchivoProcesado, MateriaPrimaExterna, TipoArchivo
from app.services.ingestion import ArchivoYaProcesadoError, hash_bytes
from app.services.parsing import clean_str, excel_engine_for, to_date

MATERIA_PRIMA_SHEET_NAME = "MATERIA PRIMA"


def _find_sheet(xl: pd.ExcelFile) -> str | None:
    target = MATERIA_PRIMA_SHEET_NAME.strip().lower()
    for name in xl.sheet_names:
        if name.strip().lower() == target:
            return name
    return None


def ingest_trazabilidad_externa(
    db: Session, raw_bytes: bytes, filename: str, usuario_id: uuid.UUID | None = None
) -> int:
    """Devuelve la cantidad de filas nuevas agregadas."""
    file_hash = hash_bytes(raw_bytes)
    existing = db.execute(
        select(ArchivoProcesado).where(
            ArchivoProcesado.nombre_archivo == filename, ArchivoProcesado.hash_contenido == file_hash
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ArchivoYaProcesadoError(f"'{filename}' ya fue procesado anteriormente.")

    engine = excel_engine_for(raw_bytes)
    xl = pd.ExcelFile(BytesIO(raw_bytes), engine=engine)
    sheet_name = _find_sheet(xl)
    if sheet_name is None:
        raise ValueError(f'No se encontró la hoja "{MATERIA_PRIMA_SHEET_NAME}" en {filename}.')

    df = xl.parse(sheet_name, header=None)
    data = df.values

    new_rows = []
    for r in range(1, len(data)):  # fila 0 = encabezado
        row = data[r]
        lote = clean_str(row[2])
        di = clean_str(row[5])
        if not lote or not di:
            continue
        new_rows.append(
            {
                "lote_interno": lote,
                "di_externo": di,
                "barco": clean_str(row[4]) if len(row) > 4 else "",
                "especie": clean_str(row[7]) if len(row) > 7 else "",
                "fecha_recalada": to_date(row[6]) if len(row) > 6 else None,
                "archivo_origen": filename,
            }
        )

    added = 0
    if new_rows:
        stmt = pg_insert(MateriaPrimaExterna).values(new_rows)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_mp_externa_dedup_key")
        stmt = stmt.returning(MateriaPrimaExterna.id)
        # rowcount no es confiable para INSERT ... ON CONFLICT con valores múltiples
        # en algunos drivers — contar las filas devueltas por RETURNING sí lo es.
        result = db.execute(stmt)
        added = len(result.fetchall())

    db.add(
        ArchivoProcesado(
            nombre_archivo=filename,
            hash_contenido=file_hash,
            tipo=TipoArchivo.TRAZABILIDAD_INTERNA,
            procesado_por_id=usuario_id,
        )
    )
    db.commit()
    return added
