"""
Cruce Lote-DI (3 vías): compara el registro interno de la planta, el lote
digitado en Sernapesca, y el DI resuelto por el algoritmo de balance.

Port 1:1 de writeCruceLoteDi() en Codigo.gs. Es una vista derivada — se
recalcula completa en cada consulta, no se persiste (igual que en el
original, donde la hoja se sh.clear()-ea y reescribe entera cada vez).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Linea, MateriaPrimaExterna, TipoLinea

_ORDEN_ESTADO = {
    "DISCREPANCIA - revisar": 0,
    "Aún no procesado en Sernapesca": 1,
    "Sin dato en registro interno": 2,
    "OK - coincide": 3,
}


@dataclass
class CruceRow:
    lote: str
    di_externo: list[str] = field(default_factory=list)
    di_resuelto: list[str] = field(default_factory=list)
    estado_cruce: str = ""
    estado_interno: str = ""
    especies: list[str] = field(default_factory=list)
    barcos: list[str] = field(default_factory=list)


def calcular_cruce_lote_di(db: Session) -> list[CruceRow]:
    resueltos: dict[str, dict] = {}
    rows = db.execute(
        select(Linea.lote, Linea.estado, Linea.di, Linea.especie).where(
            Linea.tipo_linea.in_([TipoLinea.PRODUCTO.value, TipoLinea.DESECHO.value])
        )
    ).all()
    for lote, estado, di, especie in rows:
        lote = str(lote)
        entry = resueltos.setdefault(lote, {"estado": estado, "dis": set(), "especies": set()})
        entry["estado"] = estado
        entry["dis"].add(str(di))
        entry["especies"].add(especie)

    externos: dict[str, dict] = {}
    ext_rows = db.execute(
        select(MateriaPrimaExterna.lote_interno, MateriaPrimaExterna.di_externo, MateriaPrimaExterna.barco)
    ).all()
    for lote, di, barco in ext_rows:
        lote = str(lote)
        entry = externos.setdefault(lote, {"dis": set(), "barcos": set()})
        entry["dis"].add(str(di))
        if barco:
            entry["barcos"].add(barco)

    todos_los_lotes = set(resueltos.keys()) | set(externos.keys())
    filas: list[CruceRow] = []
    for lote in todos_los_lotes:
        ext = externos.get(lote)
        res = resueltos.get(lote)
        if not ext:
            estado_cruce = "Sin dato en registro interno"
        elif not res:
            estado_cruce = "Aún no procesado en Sernapesca"
        else:
            coincide = bool(ext["dis"] & res["dis"])
            estado_cruce = "OK - coincide" if coincide else "DISCREPANCIA - revisar"

        filas.append(
            CruceRow(
                lote=lote,
                di_externo=sorted(ext["dis"]) if ext else [],
                di_resuelto=sorted(res["dis"]) if res else [],
                estado_cruce=estado_cruce,
                estado_interno=res["estado"] if res else "",
                especies=sorted(res["especies"]) if res else [],
                barcos=sorted(ext["barcos"]) if ext else [],
            )
        )

    filas.sort(key=lambda f: (_ORDEN_ESTADO.get(f.estado_cruce, 99), f.lote))
    return filas
