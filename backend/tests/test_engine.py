"""
Valida el motor de resolución Lote<->DI (app/services/engine.py), en
particular el agrupamiento por especie cuando hay producción propia — caso
real detectado en producción: la declaración 8606470 consume producto
40400 "COJINOBA DEL SUR" (producido por la declaración 8601948 a partir del
DI 481263) y termina generando 46059 "COJINOBA DEL SUR O AZUL". El catálogo
de Sernapesca usa un nombre de especie distinto para el producto entero
intermedio y para el producto final del mismo pez, lo que antes hacía que
el producto final quedara agrupado con el DI de una especie completamente
ajena (481301, presente en la misma declaración) y se le atribuyera un DI
equivocado — esto generó un Caso "a revisar" falso para el lote 13902.
"""
import datetime as dt

from app.services.engine import build_lote_events
from app.services.parsing import RawRow


def _row(**kw) -> RawRow:
    base = dict(
        row_num=0, ndecl="8606470", fecha_decl=dt.date(2026, 6, 19), matprod="Mat.Prima",
        tipo_item="Recurso", codigo_producto="", nombre="", ton=0.0, lote="", tipo_origen="",
        fecha_elab=None, agente="", ndecl_origen="", bodega="",
    )
    base.update(kw)
    return RawRow(**base)


def test_producto_de_produccion_propia_no_se_atribuye_a_di_de_especie_ajena():
    rows = [
        # DI real de una especie totalmente distinta, presente en la misma declaración.
        _row(
            codigo_producto="215", nombre="215: COJINOBA DEL SUR O AZUL", species="COJINOBA DEL SUR O AZUL",
            ton=2.039, tipo_origen="DI", ndecl_origen="481301", agente="21141",
        ),
        _row(
            matprod="Producción", tipo_item="Producto", codigo_producto="46059",
            nombre="46059: COJINOBA DEL SUR O AZUL - FILETE", species="COJINOBA DEL SUR O AZUL",
            ton=1.1, lote="13904",
        ),
        # Materia prima de producción propia: catálogo la llama "COJINOBA DEL SUR" (sin "O AZUL").
        _row(
            codigo_producto="40400", nombre="40400: COJINOBA DEL SUR", species="COJINOBA DEL SUR",
            ton=0.02, lote="13902", tipo_origen="PLA", ndecl_origen="8601948",
        ),
        # El producto que resulta de esa materia propia — mismo lote, pero el catálogo
        # lo etiqueta con la especie "O AZUL" (igual que el DI 481301 de arriba).
        _row(
            matprod="Producción", tipo_item="Producto", codigo_producto="46059",
            nombre="46059: COJINOBA DEL SUR O AZUL - FILETE", species="COJINOBA DEL SUR O AZUL",
            ton=0.01, lote="13902",
        ),
    ]

    raw_lines, unresolved = build_lote_events(rows)

    assert unresolved == []

    productos_lote_13902 = [r for r in raw_lines if r.lote == "13902" and r.tipo_linea == "Producto"]
    assert productos_lote_13902 == [], "el producto de producción propia no debe generar una línea Producto atribuida a un DI ajeno"

    productos_lote_13904 = [r for r in raw_lines if r.lote == "13904" and r.tipo_linea == "Producto"]
    assert len(productos_lote_13904) == 1
    assert productos_lote_13904[0].di == "481301"
    assert productos_lote_13904[0].ton == 1.1  # no se le sumó el 0.01 ton ajeno

    propia = [r for r in raw_lines if r.tipo_linea == "Materia Prima (Producción Propia)"]
    assert len(propia) == 1
    assert propia[0].lote == "13902"
