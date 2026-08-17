"""
Motor de resolución Lote <-> DI de origen.

Port 1:1 de buildLoteEvents() / solvePartition() / classifyLotes() en
Codigo.gs. Esta es la lógica crítica del negocio — no reinventar, solo
traducir. Ver Codigo.gs líneas 268-445 para el original comentado.
"""
from __future__ import annotations

import copy
import dataclasses
import datetime as dt
from dataclasses import dataclass, field

from app.config import settings
from app.services.parsing import RawRow, parse_producto


@dataclass
class LineaResultado:
    """Equivalente a lo que produce makeLine() en Codigo.gs — una fila de 'rawLines'."""

    lote: str
    tipo_linea: str  # TipoLinea.value
    ndecl: str
    di: str = ""
    declaracion_origen: str = ""
    agente: str = ""
    fecha_desembarque_di: dt.date | None = None
    fecha_elab_linea: dt.date | None = None
    fecha_decl: dt.date | None = None
    producto: str = ""
    especie: str = ""
    proceso_producto: str = ""
    tipo_frio: str = ""
    producto_global: str = ""
    preparacion: str = ""
    codigo_producto: str = ""
    bodega: str = ""
    ton: float = 0.0
    row_num: int = 0


@dataclass
class SinDeterminarItem:
    ndecl: str
    species: str
    fecha_decl: dt.date | None
    di_ton: list[str]
    out_ton: list[str]


@dataclass
class LoteResumen:
    lote: str
    dis: list[str]
    agentes: list[str]
    estado: str  # EstadoLote.value
    n_declaraciones: int


def make_linea(
    x: RawRow,
    tipo_linea: str,
    ndecl: str,
    lote: str,
    di: str,
    declaracion_origen: str,
    agente: str,
    fecha_desembarque_di: dt.date | None,
) -> LineaResultado:
    pp = parse_producto(x.nombre)
    return LineaResultado(
        lote=lote,
        tipo_linea=tipo_linea,
        ndecl=ndecl,
        di=di or "",
        declaracion_origen=declaracion_origen or "",
        agente=agente or "",
        fecha_desembarque_di=fecha_desembarque_di,
        fecha_elab_linea=x.fecha_elab,
        fecha_decl=x.fecha_decl,
        producto=x.nombre,
        especie=pp.especie,
        proceso_producto=pp.proceso_producto,
        tipo_frio=pp.tipo_frio,
        producto_global=pp.producto_global,
        preparacion=pp.preparacion,
        codigo_producto=x.codigo_producto,
        bodega=x.bodega,
        ton=x.ton,
        row_num=x.row_num,
    )


def solve_partition(di_events: list[RawRow], out_items: list[RawRow]) -> dict[int, int] | None:
    """
    Asigna cada out_item a un DI tal que la suma de toneladas por DI calce
    (dentro de TOL) con el tonelaje declarado de ese DI. Backtracking simple,
    igual que en Codigo.gs.
    """
    n_di = len(di_events)
    if n_di == 1:
        return {i: 0 for i in range(len(out_items))}
    if len(out_items) > 12:
        return None  # evita explosión combinatoria

    tol = settings.tolerancia_balance_ton
    targets = [d.ton for d in di_events]
    sums = [0.0] * n_di
    assign: dict[int, int] = {}
    best: dict[int, int] | None = None

    def bt(i: int):
        nonlocal best
        if best is not None:
            return
        if i == len(out_items):
            if all(abs(sums[k] - targets[k]) <= tol for k in range(n_di)):
                best = dict(assign)
            return
        ton = out_items[i].ton
        for k in range(n_di):
            if sums[k] + ton <= targets[k] + tol:
                sums[k] += ton
                assign[i] = k
                bt(i + 1)
                sums[k] -= ton
                del assign[i]
                if best is not None:
                    return

    bt(0)
    return best


def build_lote_events(rows: list[RawRow]) -> tuple[list[LineaResultado], list[SinDeterminarItem]]:
    """Devuelve (raw_lines, unresolved) — ver buildLoteEvents() en Codigo.gs."""
    by_decl: dict[str, list[RawRow]] = {}
    for x in rows:
        by_decl.setdefault(x.ndecl, []).append(x)

    raw_lines: list[LineaResultado] = []
    unresolved: list[SinDeterminarItem] = []

    for ndecl, items in by_decl.items():
        by_species: dict[str, list[RawRow]] = {}
        for x in items:
            by_species.setdefault(x.species, []).append(x)

        for species, srows in by_species.items():
            raw_di_events = [x for x in srows if x.matprod == "Mat.Prima" and x.tipo_origen == "DI"]

            # Fusiona líneas de Mat.Prima que comparten el mismo DI (suma toneladas).
            merged_map: dict[str, RawRow] = {}
            merged_order: list[str] = []
            for x in raw_di_events:
                key = x.ndecl_origen
                if key not in merged_map:
                    merged_map[key] = dataclasses.replace(x)
                    merged_order.append(key)
                else:
                    merged_map[key].ton += x.ton
            di_events = [merged_map[k] for k in merged_order]

            # Materia prima de producción propia: reprocesa un lote ya existente.
            propia_rows = [x for x in srows if x.matprod == "Mat.Prima" and x.tipo_origen == "PLA"]
            pla_lotes = {x.lote for x in propia_rows if x.lote}

            def registrar_propia():
                for x in propia_rows:
                    raw_lines.append(
                        make_linea(
                            x, "Materia Prima (Producción Propia)", ndecl, x.lote, "",
                            x.ndecl_origen, x.agente, None,
                        )
                    )

            out_items = [x for x in srows if x.matprod == "Producción" and x.lote not in pla_lotes]

            if len(di_events) == 0 or len(out_items) == 0:
                registrar_propia()
                continue

            assign = solve_partition(di_events, out_items)
            if assign is None:
                unresolved.append(
                    SinDeterminarItem(
                        ndecl=ndecl,
                        species=species,
                        fecha_decl=items[0].fecha_decl,
                        di_ton=[f"{d.ndecl_origen}: {d.ton} ton" for d in di_events],
                        out_ton=[f"{(o.lote or '(desecho)')}: {o.ton} ton (fila {o.row_num})" for o in out_items],
                    )
                )
                registrar_propia()
                continue

            # agrupar los items asignados por lote de origen (índice de DI)
            por_batch: list[list[RawRow]] = [[] for _ in di_events]
            for i, out in enumerate(out_items):
                por_batch[assign[i]].append(out)

            for bi, di in enumerate(di_events):
                asignados = por_batch[bi]
                # lote "dominante" del batch: el primer lote no vacío entre sus productos reales
                lote_dominante = next((o.lote for o in asignados if o.lote), "")

                raw_lines.append(
                    make_linea(
                        di, "Materia Prima (DI)", ndecl, lote_dominante, di.ndecl_origen, "", di.agente, di.fecha_elab,
                    )
                )

                for out in asignados:
                    if out.lote:
                        raw_lines.append(
                            make_linea(out, "Producto", ndecl, out.lote, di.ndecl_origen, "", di.agente, di.fecha_elab)
                        )
                    else:
                        # desecho sin lote digitado -> hereda el lote dominante del batch
                        raw_lines.append(
                            make_linea(
                                out, "Desecho", ndecl, lote_dominante, di.ndecl_origen, "", di.agente, di.fecha_elab,
                            )
                        )

            registrar_propia()

    return raw_lines, unresolved


def classify_lotes(raw_lines: list[LineaResultado]) -> list[LoteResumen]:
    """
    Clasifica cada Lote en OK / OK-parcial / REVISAR según los DI que aparecen
    en sus líneas de tipo Producto o Desecho.
    """
    by_lote: dict[str, list[LineaResultado]] = {}
    for r in raw_lines:
        if r.tipo_linea not in ("Producto", "Desecho"):
            continue
        if not r.lote:
            continue
        by_lote.setdefault(r.lote, []).append(r)

    resumen: list[LoteResumen] = []
    for lote, evs in by_lote.items():
        dis = sorted({e.di for e in evs})
        agentes = sorted({e.agente for e in evs})
        if len(dis) == 1:
            estado = "OK - un solo DI"
        elif len(agentes) == 1:
            estado = "OK - mismo barco, DI parcial+definitivo"
        else:
            estado = "REVISAR - DI de barcos distintos"
        resumen.append(
            LoteResumen(
                lote=lote,
                dis=dis,
                agentes=agentes,
                estado=estado,
                n_declaraciones=len({e.ndecl for e in evs}),
            )
        )

    resumen.sort(key=lambda r: (0 if r.estado.startswith("REVISAR") else 1, r.lote))
    return resumen
