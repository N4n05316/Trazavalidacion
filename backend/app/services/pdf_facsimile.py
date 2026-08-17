"""
Genera el PDF facsímil de una declaración (sección 8 del brief): mismo
layout de dos columnas Materia | Producto que el "REPORTE PLANTA
PRODUCCIÓN" oficial de Sernapesca, pero con membrete propio de Certus — a
propósito NO se reproduce el escudo, sello ni código de verificación
oficiales de Sernapesca, ya que esos elementos certifican la autenticidad
del documento GUBERNAMENTAL original; este PDF es una reconstrucción
interna a partir de los datos ya digitados, para revisión visual, no un
reemplazo del documento oficial.
"""
from __future__ import annotations

import datetime as dt
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.facsimile import DeclaracionFacsimile

_BRASS = colors.HexColor("#8a6a3a")
_PETROL = colors.HexColor("#0b1e26")
_LINE = colors.HexColor("#c9c9c9")

_styles = getSampleStyleSheet()
_h1 = ParagraphStyle("CertusH1", parent=_styles["Heading1"], fontSize=15, textColor=_PETROL, spaceAfter=2)
_meta = ParagraphStyle("CertusMeta", parent=_styles["Normal"], fontSize=9, textColor=colors.HexColor("#444444"))
_sectionTitle = ParagraphStyle(
    "CertusSection", parent=_styles["Heading3"], fontSize=10, textColor=colors.white, backColor=_PETROL,
    leftIndent=4, spaceAfter=0, spaceBefore=0,
)
_cell = ParagraphStyle("CertusCell", parent=_styles["Normal"], fontSize=8, leading=10.5)
_footnote = ParagraphStyle("CertusFootnote", parent=_styles["Normal"], fontSize=7, textColor=colors.HexColor("#777777"))


def _fmt_fecha(d: dt.date | None) -> str:
    return d.strftime("%d-%m-%Y") if d else "—"


def _materia_html(fila) -> str:
    partes = []
    for b in fila.materia:
        lote_txt = f' — Lote <font color="#8a6a3a"><b>{b.lote_resuelto}</b></font>' if b.lote_resuelto else ""
        partes.append(f"• <b>{b.codigo}</b>: {b.especie} — {b.etiqueta}{lote_txt} — {b.ton:g} ton.")
    return "<br/>".join(partes) if partes else "—"


def _fila_lote_resuelto(fila) -> str:
    """El lote dominante ya calculado para esta fila (mismo para todos sus bullets de materia)."""
    for b in fila.materia:
        if b.lote_resuelto:
            return b.lote_resuelto
    return ""


def _producto_html(fila) -> str:
    lote_esperado = _fila_lote_resuelto(fila)
    partes = []
    for p in fila.producto:
        discrepa = bool(lote_esperado and p.lote and p.lote != lote_esperado)
        lote_html = f'<font color="#c1594c"><b>{p.lote}</b></font>' if discrepa else f"<b>{p.lote or '(sin lote)'}</b>"
        partes.append(
            f"• <b>{p.codigo}</b>: {p.nombre_corto}<br/>"
            f"&nbsp;&nbsp;Fecha elab.: {_fmt_fecha(p.fecha_elaboracion)} — "
            f"Lote: {lote_html} — {p.ton:g} ton."
        )
    return "<br/>".join(partes) if partes else "—"


def generar_pdf_facsimile(facsimile: DeclaracionFacsimile) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=16 * mm, bottomMargin=14 * mm, leftMargin=14 * mm, rightMargin=14 * mm,
        title=f"Facsímil declaración {facsimile.n_declaracion}",
    )

    story = []
    story.append(Paragraph("Certus — Facsímil de Declaración", _h1))
    story.append(
        Paragraph(
            "Reconstrucción interna a partir de los datos digitados en Sernapesca — no es un documento oficial.",
            _meta,
        )
    )
    story.append(Spacer(1, 8 * mm))

    header_data = [
        ["N° Declaración (Folio)", facsimile.n_declaracion, "Fecha Declaración", _fmt_fecha(facsimile.fecha_declaracion)],
        ["Planta", "PESQUERA FRIOSUR SpA", "N° Registro / RUT", "11004 / 86577500-8"],
        ["Dirección", "José María Caro 300, Puerto Chacabuco", "Región", "XI"],
    ]
    header_table = Table(header_data, colWidths=[38 * mm, 62 * mm, 38 * mm, 52 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), _BRASS),
                ("TEXTCOLOR", (2, 0), (2, -1), _BRASS),
                ("GRID", (0, 0), (-1, -1), 0.5, _LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("&nbsp;DETALLE", _sectionTitle))
    story.append(Spacer(1, 2))

    detalle_data = [[Paragraph("<b>Materia</b>", _cell), Paragraph("<b>Producto</b>", _cell)]]
    for fila in facsimile.filas:
        detalle_data.append([Paragraph(_materia_html(fila), _cell), Paragraph(_producto_html(fila), _cell)])

    if len(detalle_data) == 1:
        detalle_data.append([Paragraph("Sin líneas registradas.", _cell), Paragraph("", _cell)])

    detalle_table = Table(detalle_data, colWidths=[95 * mm, 95 * mm], repeatRows=1)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, _LINE),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9e9e9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    detalle_table.setStyle(TableStyle(style))
    story.append(detalle_table)

    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            f"Generado por Certus el {dt.datetime.now().strftime('%d-%m-%Y %H:%M')} — "
            f"declaración N° {facsimile.n_declaracion}. Los lotes mostrados son los digitados originalmente, "
            "sin corrección.",
            _footnote,
        )
    )

    doc.build(story)
    return buffer.getvalue()
