"""
Orquesta: parseo -> motor de resolución -> persistencia.

Port 1:1 del flujo procesarReporteProduccion() / writeResults() /
writeHistorial() / writeActividadDiaria() / writeUnresolvedSheet() de
Codigo.gs, adaptado a un modelo relacional:

  - "Detalle completo" (acumulativo, dedup por clave) -> tabla `lineas`,
    con UNIQUE constraint haciendo de appendDedup().
  - "Sin determinar" (se reescribe cada corrida) -> filas `sin_determinar`
    ligadas a la `ejecucion` que las generó (no se borra nada del pasado,
    simplemente cada ejecución tiene las suyas).
  - "Historial de Ejecuciones" -> tabla `ejecuciones`.
  - "Historial de Casos" (un lote a revisar se registra UNA sola vez, sin
    tocar anotaciones manuales existentes) -> tabla `casos`, con
    ON CONFLICT DO NOTHING sobre `lote`.
  - "Productividad Diaria" (upsert por fecha, el archivo más reciente pisa
    al anterior para esa fecha) -> tabla `productividad_diaria`.
"""
from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import (
    ArchivoProcesado,
    Caso,
    Ejecucion,
    EstadoLote,
    Linea,
    LineaCruda,
    ProductividadDiaria,
    SinDeterminar,
    TipoArchivo,
    TipoLinea,
)
from app.services.engine import LineaResultado, LoteResumen, build_lote_events, classify_lotes
from app.services.parsing import RawRow, parse_rows


class ArchivoYaProcesadoError(Exception):
    pass


def hash_bytes(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _estado_de(r: LineaResultado, estado_por_lote: dict[str, str]) -> str:
    if r.lote and r.lote in estado_por_lote:
        return estado_por_lote[r.lote]
    if r.tipo_linea == TipoLinea.MATERIA_PRIMA_PROPIA.value:
        return EstadoLote.NA_LINEA_CONSUMO.value
    if r.tipo_linea == TipoLinea.MATERIA_PRIMA_DI.value and not r.lote:
        return EstadoLote.NA_LOTE_NO_DETERMINADO.value
    return EstadoLote.NA_LOTE_NO_RESUELTO.value if r.lote else EstadoLote.NA.value


def _build_actividad_diaria(rows: list[RawRow]) -> dict:
    by_date: dict = {}
    for x in rows:
        key = x.fecha_decl
        if not key:
            continue
        d = by_date.setdefault(
            key,
            {"ndecls": set(), "n_lineas": 0, "n_mp": 0, "n_prod": 0, "dis": set(), "especies": set(), "ton_prod": 0.0, "ton_mp": 0.0},
        )
        d["ndecls"].add(x.ndecl)
        d["n_lineas"] += 1
        d["especies"].add(x.species)
        if x.matprod == "Mat.Prima":
            d["n_mp"] += 1
            d["ton_mp"] += x.ton
            if x.tipo_origen == "DI" and x.ndecl_origen:
                d["dis"].add(x.ndecl_origen)
        elif x.matprod == "Producción":
            d["n_prod"] += 1
            d["ton_prod"] += x.ton
    return by_date


def ingest_reporte_produccion(
    db: Session, raw_bytes: bytes, filename: str, usuario_id: uuid.UUID | None = None
) -> Ejecucion:
    file_hash = hash_bytes(raw_bytes)
    existing = db.execute(
        select(ArchivoProcesado).where(
            ArchivoProcesado.nombre_archivo == filename, ArchivoProcesado.hash_contenido == file_hash
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ArchivoYaProcesadoError(f"'{filename}' ya fue procesado anteriormente.")

    rows = parse_rows(raw_bytes, filename)
    raw_lines, unresolved = build_lote_events(rows)
    resumen = classify_lotes(raw_lines)

    # ---- 1) Detalle completo (dedup vía UNIQUE constraint) ----
    estado_por_lote = {r.lote: r.estado for r in resumen}
    linea_rows = [
        {
            "lote": r.lote,
            "tipo_linea": r.tipo_linea,
            "estado": _estado_de(r, estado_por_lote),
            "n_declaracion": r.ndecl,
            "di": r.di,
            "declaracion_origen": r.declaracion_origen,
            "agente": r.agente,
            "fecha_desembarque_di": r.fecha_desembarque_di,
            "fecha_elaboracion_linea": r.fecha_elab_linea,
            "fecha_declaracion": r.fecha_decl,
            "producto": r.producto,
            "especie": r.especie,
            "proceso_producto": r.proceso_producto,
            "tipo_frio": r.tipo_frio,
            "producto_global": r.producto_global,
            "preparacion": r.preparacion,
            "codigo_producto": r.codigo_producto,
            "nombre_bodega": r.bodega,
            "toneladas": r.ton,
            "fila_original": r.row_num,
            "archivo_origen": filename,
        }
        for r in raw_lines
    ]
    if linea_rows:
        stmt = pg_insert(Linea).values(linea_rows)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_linea_dedup_key")
        db.execute(stmt)

    # ---- 2) Registrar archivo procesado + ejecución ----
    archivo = ArchivoProcesado(
        nombre_archivo=filename,
        hash_contenido=file_hash,
        tipo=TipoArchivo.PRODUCCION,
        procesado_por_id=usuario_id,
    )
    db.add(archivo)
    db.flush()

    # ---- 1b) Copia cruda fila-a-fila (ver LineaCruda) — fuente para el facsímil PDF ----
    cruda_rows = [
        {
            "archivo_id": archivo.id,
            "fila_original": x.row_num,
            "n_declaracion": x.ndecl,
            "fecha_declaracion": x.fecha_decl,
            "matprod": x.matprod,
            "tipo_item": x.tipo_item,
            "codigo_producto": x.codigo_producto,
            "nombre": x.nombre,
            "especie": x.species,
            "toneladas": x.ton,
            "lote": x.lote,
            "tipo_origen": x.tipo_origen,
            "fecha_elaboracion": x.fecha_elab,
            "agente": x.agente,
            "declaracion_origen": x.ndecl_origen,
            "nombre_bodega": x.bodega,
        }
        for x in rows
    ]
    if cruda_rows:
        stmt = pg_insert(LineaCruda).values(cruda_rows)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_linea_cruda_declaracion_fila")
        db.execute(stmt)

    n_ok = sum(1 for r in resumen if r.estado == EstadoLote.OK_UN_DI.value)
    n_ok2 = sum(1 for r in resumen if "parcial" in r.estado)
    n_revisar = sum(1 for r in resumen if r.estado.startswith("REVISAR"))

    ejecucion = Ejecucion(
        archivo_id=archivo.id,
        archivo_nombre=filename,
        lotes_ok=n_ok,
        lotes_ok_parcial=n_ok2,
        lotes_revisar=n_revisar,
        lotes_sin_determinar=len(resumen) - n_ok - n_ok2 - n_revisar,
    )
    db.add(ejecucion)
    db.flush()

    # ---- 3) Sin determinar (ligado a esta ejecución) ----
    for u in unresolved:
        db.add(
            SinDeterminar(
                ejecucion_id=ejecucion.id,
                n_declaracion=u.ndecl,
                especie=u.species,
                fecha_declaracion=u.fecha_decl,
                di_toneladas="; ".join(u.di_ton),
                out_toneladas="; ".join(u.out_ton),
            )
        )

    # ---- 4) Historial de Casos: cada lote a revisar, UNA sola vez ----
    casos_revisar = [r for r in resumen if r.estado.startswith("REVISAR")]
    if casos_revisar:
        caso_rows = [
            {
                "lote": r.lote,
                "di_asociados": ", ".join(r.dis),
                "agentes": ", ".join(r.agentes),
                "n_declaraciones": r.n_declaraciones,
            }
            for r in casos_revisar
        ]
        stmt = pg_insert(Caso).values(caso_rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["lote"])
        db.execute(stmt)

    # ---- 5) Productividad diaria (upsert por fecha) ----
    actividad = _build_actividad_diaria(rows)
    for fecha, d in actividad.items():
        stmt = pg_insert(ProductividadDiaria).values(
            fecha=fecha,
            n_declaraciones=len(d["ndecls"]),
            n_lineas_totales=d["n_lineas"],
            n_lineas_materia_prima=d["n_mp"],
            n_lineas_produccion=d["n_prod"],
            n_di_distintos=len(d["dis"]),
            n_especies_distintas=len(d["especies"]),
            toneladas_producto=round(d["ton_prod"], 3),
            toneladas_materia_prima=round(d["ton_mp"], 3),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["fecha"],
            set_={
                "n_declaraciones": stmt.excluded.n_declaraciones,
                "n_lineas_totales": stmt.excluded.n_lineas_totales,
                "n_lineas_materia_prima": stmt.excluded.n_lineas_materia_prima,
                "n_lineas_produccion": stmt.excluded.n_lineas_produccion,
                "n_di_distintos": stmt.excluded.n_di_distintos,
                "n_especies_distintas": stmt.excluded.n_especies_distintas,
                "toneladas_producto": stmt.excluded.toneladas_producto,
                "toneladas_materia_prima": stmt.excluded.toneladas_materia_prima,
            },
        )
        db.execute(stmt)

    db.commit()
    db.refresh(ejecucion)
    return ejecucion
