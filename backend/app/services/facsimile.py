"""
Reconstruye una declaración tal cual fue digitada, para el PDF facsímil
(sección 8 del brief) — SIEMPRE desde `lineas_crudas` (ver LineaCruda), no
desde la tabla resuelta `lineas`, precisamente para no depender de lo que el
algoritmo de validación haya logrado clasificar. Muestra el lote digitado
por la persona, sin corrección.

Agrupación visual (Materia junto a su Producto correspondiente): para
especies con SOLO materia prima por DI, se reutiliza el mismo algoritmo de
calce por balance de toneladas (solve_partition) que usa el motor de
resolución — ya validado contra folios reales — así el facsímil y la
clasificación real siempre coinciden. Cuando una especie mezcla DI y
producción propia en la misma declaración, Sernapesca no expone ninguna
clave que permita separar de forma confiable qué producto vino de cuál, así
que se muestra todo junto para esa especie en vez de arriesgar una
separación incorrecta.

Lote esperado por DI (para el resaltado de discrepancias): se calcula GLOBAL,
no dentro de esta única declaración. Si se tomara el lote de esta misma
declaración como "correcto", una declaración donde TODAS las líneas están
mal digitadas (el caso real que motivó esto: DI 481820 —que en el resto del
sistema siempre corresponde al lote 13929— aparece acá con las 4 líneas mal
tipeadas como 13931) no tendría ninguna señal local con la cual compararse,
y el facsímil terminaría validando el propio error. Se usa en cambio el lote
más frecuente para ese DI en toda la tabla `lineas` — la misma señal que ya
hace que Certus marque esos lotes como "a revisar".
"""
from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Linea, LineaCruda, TipoLinea
from app.services.engine import solve_partition
from app.services.parsing import RawRow, parse_producto


@dataclass
class MateriaBullet:
    codigo: str
    especie: str
    etiqueta: str
    ton: float
    lote_resuelto: str = ""  # lote esperado para este DI según el resto del sistema — para comparar de un vistazo


@dataclass
class ProductoItem:
    codigo: str
    nombre_corto: str
    fecha_elaboracion: dt.date | None
    lote: str
    ton: float


@dataclass
class FilaFacsimile:
    materia: list[MateriaBullet] = field(default_factory=list)
    producto: list[ProductoItem] = field(default_factory=list)


@dataclass
class DeclaracionFacsimile:
    n_declaracion: str
    fecha_declaracion: dt.date | None
    filas: list[FilaFacsimile]


def _to_raw_row(lc: LineaCruda, especie: str) -> RawRow:
    return RawRow(
        row_num=0,
        ndecl=lc.n_declaracion,
        fecha_decl=lc.fecha_declaracion,
        matprod=lc.matprod,
        tipo_item=lc.tipo_item,
        codigo_producto=lc.codigo_producto,
        nombre=lc.nombre,
        ton=lc.toneladas,
        lote=lc.lote,
        tipo_origen=lc.tipo_origen,
        fecha_elab=lc.fecha_elaboracion,
        agente=lc.agente,
        ndecl_origen=lc.declaracion_origen,
        bodega=lc.nombre_bodega,
        species=especie,
    )


def _producto_item(lc: LineaCruda) -> ProductoItem:
    pp = parse_producto(lc.nombre)
    nombre_corto = f"{pp.especie} - {pp.producto_global}, {pp.preparacion}".strip(" ,")
    return ProductoItem(
        codigo=lc.codigo_producto,
        nombre_corto=nombre_corto,
        fecha_elaboracion=lc.fecha_elaboracion,
        lote=lc.lote,
        ton=lc.toneladas,
    )


def _materia_bullet_di(lc: LineaCruda, lote_resuelto: str = "") -> MateriaBullet:
    return MateriaBullet(
        codigo=lc.codigo_producto, especie=lc.especie, etiqueta=f"Recurso — DI {lc.declaracion_origen}",
        ton=lc.toneladas, lote_resuelto=lote_resuelto,
    )


def _materia_bullet_propia(lc: LineaCruda) -> MateriaBullet:
    return MateriaBullet(
        codigo=lc.codigo_producto,
        especie=lc.especie,
        etiqueta=f"Producción Propia — Declaración origen {lc.declaracion_origen}",
        ton=lc.toneladas,
    )


def _lote_esperado_por_di(db: Session, dis: set[str]) -> dict[str, str]:
    """Para cada DI, el lote más frecuente entre TODAS las declaraciones del sistema (no solo esta)."""
    dis = {d for d in dis if d}
    if not dis:
        return {}
    filas = db.execute(
        select(Linea.di, Linea.lote).where(
            Linea.di.in_(dis), Linea.tipo_linea.in_([TipoLinea.PRODUCTO.value, TipoLinea.DESECHO.value]), Linea.lote != ""
        )
    ).all()
    conteos: dict[str, Counter] = {}
    for di, lote in filas:
        conteos.setdefault(di, Counter())[lote] += 1
    return {di: contador.most_common(1)[0][0] for di, contador in conteos.items()}


def build_facsimile(db: Session, n_declaracion: str) -> DeclaracionFacsimile | None:
    rows = (
        db.execute(select(LineaCruda).where(LineaCruda.n_declaracion == n_declaracion).order_by(LineaCruda.fila_original))
        .scalars()
        .all()
    )
    if not rows:
        return None

    fecha_declaracion = rows[0].fecha_declaracion

    dis_presentes = {r.declaracion_origen for r in rows if r.matprod == "Mat.Prima" and r.tipo_origen == "DI"}
    lote_esperado = _lote_esperado_por_di(db, dis_presentes)

    by_species: dict[str, list[LineaCruda]] = {}
    for r in rows:
        by_species.setdefault(r.especie, []).append(r)

    filas: list[FilaFacsimile] = []

    for especie, srows in by_species.items():
        di_raw = [r for r in srows if r.matprod == "Mat.Prima" and r.tipo_origen == "DI"]
        propia_raw = [r for r in srows if r.matprod == "Mat.Prima" and r.tipo_origen == "PLA"]
        propia_lotes = {r.lote for r in propia_raw if r.lote}
        out_raw = [r for r in srows if r.matprod == "Producción" and r.lote not in propia_lotes]

        if propia_raw:
            # Especie con producción propia (con o sin DI también) — no se separa,
            # ver docstring del módulo.
            fila = FilaFacsimile()
            for r in di_raw:
                fila.materia.append(_materia_bullet_di(r, lote_esperado.get(r.declaracion_origen, "")))
            for r in propia_raw:
                fila.materia.append(_materia_bullet_propia(r))
            for r in out_raw:
                fila.producto.append(_producto_item(r))
            if fila.materia or fila.producto:
                filas.append(fila)
            continue

        if not di_raw or not out_raw:
            if di_raw or out_raw:
                fila = FilaFacsimile()
                for r in di_raw:
                    fila.materia.append(_materia_bullet_di(r, lote_esperado.get(r.declaracion_origen, "")))
                for r in out_raw:
                    fila.producto.append(_producto_item(r))
                filas.append(fila)
            continue

        # Fusiona por DI (mismo criterio que build_lote_events) solo para calcular
        # el calce — el detalle crudo (sin fusionar) se usa igual para mostrar.
        merged_order: list[str] = []
        merged_sources: dict[str, list[LineaCruda]] = {}
        for r in di_raw:
            key = r.declaracion_origen
            if key not in merged_sources:
                merged_sources[key] = []
                merged_order.append(key)
            merged_sources[key].append(r)

        di_events = [
            RawRow(
                row_num=0, ndecl=n_declaracion, fecha_decl=fecha_declaracion, matprod="Mat.Prima", tipo_item="Recurso",
                codigo_producto=merged_sources[key][0].codigo_producto, nombre=merged_sources[key][0].nombre,
                ton=sum(r.toneladas for r in merged_sources[key]), lote="", tipo_origen="DI",
                fecha_elab=merged_sources[key][0].fecha_elaboracion, agente=merged_sources[key][0].agente,
                ndecl_origen=key, bodega=merged_sources[key][0].nombre_bodega, species=especie,
            )
            for key in merged_order
        ]
        out_items = [_to_raw_row(r, especie) for r in out_raw]

        assign = solve_partition(di_events, out_items)

        if assign is None:
            fila = FilaFacsimile()
            for r in di_raw:
                fila.materia.append(_materia_bullet_di(r, lote_esperado.get(r.declaracion_origen, "")))
            for r in out_raw:
                fila.producto.append(_producto_item(r))
            filas.append(fila)
            continue

        por_batch: list[list[LineaCruda]] = [[] for _ in di_events]
        for i, out_lc in enumerate(out_raw):
            por_batch[assign[i]].append(out_lc)

        for bi, key in enumerate(merged_order):
            fila = FilaFacsimile()
            for sub in merged_sources[key]:
                fila.materia.append(_materia_bullet_di(sub, lote_esperado.get(key, "")))
            for out_lc in por_batch[bi]:
                fila.producto.append(_producto_item(out_lc))
            filas.append(fila)

    return DeclaracionFacsimile(n_declaracion=n_declaracion, fecha_declaracion=fecha_declaracion, filas=filas)
