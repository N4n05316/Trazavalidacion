"""Consultas de soporte para los reportes de la sección 7 del brief."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Linea, TipoLinea
from app.schemas import BalanceMasaOut


def resumen_ejecutivo(db: Session, top_especies: int = 7) -> dict:
    """
    Resumen acumulado (todos los archivos procesados hasta ahora), equivalente
    a la hoja 'Resumen' en Codigo.gs: cuenta de lotes por estado (única por
    lote, tomando el último estado visto — igual que el original), y las
    especies con más toneladas trazadas.
    """
    filas = db.execute(
        select(Linea.lote, Linea.estado).where(
            Linea.tipo_linea.in_([TipoLinea.PRODUCTO.value, TipoLinea.DESECHO.value])
        )
    ).all()
    por_lote: dict[str, str] = {}
    for lote, estado in filas:
        por_lote[lote] = estado  # el último visto gana, igual que writeResumenSheet()

    estados = list(por_lote.values())
    n_ok = sum(1 for e in estados if e == "OK - un solo DI")
    n_ok2 = sum(1 for e in estados if "parcial" in e)
    n_revisar = sum(1 for e in estados if e.startswith("REVISAR"))

    especie_rows = db.execute(
        select(Linea.especie, func.sum(Linea.toneladas)).group_by(Linea.especie).order_by(func.sum(Linea.toneladas).desc()).limit(top_especies)
    ).all()

    return {
        "lotes_ok": n_ok,
        "lotes_ok_parcial": n_ok2,
        "lotes_revisar": n_revisar,
        "total_lotes": len(estados),
        "especies": [{"especie": e, "toneladas": round(float(t), 3)} for e, t in especie_rows],
    }


def balance_masa(
    db: Session, di: str | None = None, lote: str | None = None, n_declaracion: str | None = None
) -> list[BalanceMasaOut]:
    """
    Balance de masa por DI, Lote o N° de Declaración (sección 7.2): para cada
    declaración involucrada, cuánta materia prima entró vs. cuánto producto +
    desecho salió — la misma comparación que hace el algoritmo de balance de
    toneladas (solve_partition), pero expuesta de forma transparente.
    """
    if not di and not lote and not n_declaracion:
        return []

    conditions = []
    if di:
        conditions.append(Linea.di == di)
    if lote:
        conditions.append(Linea.lote == lote)
    if n_declaracion:
        conditions.append(Linea.n_declaracion == n_declaracion)

    rows = db.execute(select(Linea).where(or_(*conditions))).scalars().all()

    # agrupar por declaración, ya que un mismo DI/lote puede aparecer en varias
    grupos: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"mp": 0.0, "prod": 0.0, "desecho": 0.0}
    )
    for r in rows:
        key = (r.n_declaracion, r.di, r.lote, r.especie)
        if r.tipo_linea == TipoLinea.MATERIA_PRIMA_DI.value:
            grupos[key]["mp"] += r.toneladas
        elif r.tipo_linea == TipoLinea.PRODUCTO.value:
            grupos[key]["prod"] += r.toneladas
        elif r.tipo_linea == TipoLinea.DESECHO.value:
            grupos[key]["desecho"] += r.toneladas

    out = []
    for (ndecl, di_, lote_, especie), v in sorted(grupos.items()):
        out.append(
            BalanceMasaOut(
                n_declaracion=ndecl,
                di=di_,
                lote=lote_,
                especie=especie,
                materia_prima_ton=round(v["mp"], 3),
                producto_ton=round(v["prod"], 3),
                desecho_ton=round(v["desecho"], 3),
                balance=round(v["mp"] - (v["prod"] + v["desecho"]), 3),
            )
        )
    return out
