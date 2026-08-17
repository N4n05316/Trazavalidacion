import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ejecucion, Linea, ProductividadDiaria, TipoLinea
from app.schemas import CruceLoteDiOut, EjecucionOut, LineaOut, ProductividadDiariaOut
from app.services.cruce import calcular_cruce_lote_di
from app.services.excel_export import generar_excel_auditoria
from app.services.facsimile import build_facsimile
from app.services.pdf_facsimile import generar_pdf_facsimile
from app.services.reportes import balance_masa, resumen_ejecutivo

router = APIRouter(prefix="/api/reportes", tags=["reportes"])


@router.get("/resumen")
def reporte_resumen(db: Session = Depends(get_db)):
    """Resumen ejecutivo acumulado — KPIs para el dashboard principal."""
    return resumen_ejecutivo(db)


@router.get("/incumplimientos", response_model=list[LineaOut])
def reporte_incumplimientos(
    solo_revisar: bool = True,
    lote: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Sección 7.1: lotes marcados 'a revisar' (con OK visibles si solo_revisar=False).
    Devuelve las líneas de Producto/Desecho — el detalle de DI(s), agente(s) y
    declaraciones se puede derivar agrupando por lote en el cliente, o consultar
    /api/casos para la vista ya agregada con estado de revisión manual. Filtrar
    por `lote` para el detalle de declaraciones de un caso puntual.
    """
    stmt = select(Linea).where(Linea.tipo_linea.in_([TipoLinea.PRODUCTO.value, TipoLinea.DESECHO.value]))
    if solo_revisar:
        stmt = stmt.where(Linea.estado.like("REVISAR%"))
    if lote:
        stmt = stmt.where(Linea.lote == lote)
    stmt = stmt.order_by(Linea.fecha_declaracion.desc())
    return db.execute(stmt).scalars().all()


@router.get("/balance-masa")
def reporte_balance_masa(
    di: str | None = Query(default=None),
    lote: str | None = Query(default=None),
    n_declaracion: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Sección 7.2: balance de masa (materia prima vs. producto + desecho) por DI, Lote o N° de Declaración."""
    return balance_masa(db, di=di, lote=lote, n_declaracion=n_declaracion)


@router.get("/declaraciones", response_model=list[ProductividadDiariaOut])
def reporte_declaraciones(
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
    db: Session = Depends(get_db),
):
    """Sección 7.3: productividad diaria de digitación (agregada por día)."""
    stmt = select(ProductividadDiaria).order_by(ProductividadDiaria.fecha)
    if desde:
        stmt = stmt.where(ProductividadDiaria.fecha >= desde)
    if hasta:
        stmt = stmt.where(ProductividadDiaria.fecha <= hasta)
    return db.execute(stmt).scalars().all()


@router.get("/cruce-lote-di", response_model=list[CruceLoteDiOut])
def reporte_cruce_lote_di(db: Session = Depends(get_db)):
    """Sección 7.4: cruce de 3 vías (registro interno / lote digitado / DI resuelto)."""
    filas = calcular_cruce_lote_di(db)
    return [
        CruceLoteDiOut(
            lote=f.lote,
            di_externo=f.di_externo,
            di_resuelto=f.di_resuelto,
            estado_cruce=f.estado_cruce,
            estado_interno=f.estado_interno,
            especies=f.especies,
            barcos=f.barcos,
            fecha=f.fecha,
        )
        for f in filas
    ]


@router.get("/ejecuciones", response_model=list[EjecucionOut])
def historial_ejecuciones(db: Session = Depends(get_db)):
    stmt = select(Ejecucion).order_by(Ejecucion.fecha_ejecucion.desc())
    return db.execute(stmt).scalars().all()


@router.get("/exportar.xlsx")
def exportar_excel(db: Session = Depends(get_db)):
    """Sección 6.6: Excel de auditoría exportable, para revisión offline o adjuntar en un correo."""
    contenido = generar_excel_auditoria(db)
    fecha = dt.date.today().isoformat()
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="certus_auditoria_{fecha}.xlsx"'},
    )


@router.get("/facsimil/{n_declaracion}.pdf")
def facsimil_declaracion(n_declaracion: str, db: Session = Depends(get_db)):
    """Sección 8: PDF facsímil de la declaración tal cual fue digitada."""
    facsimile = build_facsimile(db, n_declaracion)
    if facsimile is None:
        raise HTTPException(status_code=404, detail=f"No hay datos para la declaración {n_declaracion}")
    pdf_bytes = generar_pdf_facsimile(facsimile)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="facsimil_{n_declaracion}.pdf"'},
    )
