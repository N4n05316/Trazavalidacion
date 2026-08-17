"""
Smoke tests de los endpoints de reportes contra datos reales en `lineas` — no
para validar el cálculo (ver test_engine.py) sino para atrapar
desincronizaciones entre el dataclass/servicio y el schema de salida (ej. un
campo agregado al schema pero no al constructor del router, que rompe recién
en runtime porque los tests existentes no ejercitaban estos endpoints con datos).
"""
import datetime as dt
import uuid

from app.models import EstadoLote, Linea, TipoLinea


def _linea(**kw) -> Linea:
    base = dict(
        id=uuid.uuid4(), lote="9001", tipo_linea=TipoLinea.PRODUCTO.value, estado=EstadoLote.OK_UN_DI.value,
        n_declaracion="9999999", di="500000", declaracion_origen="", agente="12345",
        fecha_declaracion=dt.date(2026, 1, 15), producto="Prueba", especie="ESPECIE DE PRUEBA",
        codigo_producto="1", nombre_bodega="", toneladas=1.0, fila_original=1, archivo_origen="test",
    )
    base.update(kw)
    return Linea(**base)


def test_cruce_lote_di_incluye_fecha(client, usuario_admin, db):
    db.add(_linea())
    db.commit()

    res = client.get("/api/reportes/cruce-lote-di", headers=_auth(client, usuario_admin))
    assert res.status_code == 200
    fila = next(f for f in res.json() if f["lote"] == "9001")
    assert fila["fecha"] == "2026-01-15"


def test_balance_masa_por_n_declaracion(client, usuario_admin, db):
    db.add(_linea(tipo_linea=TipoLinea.MATERIA_PRIMA_DI.value, toneladas=2.0))
    db.add(_linea(id=uuid.uuid4(), fila_original=2, tipo_linea=TipoLinea.PRODUCTO.value, toneladas=1.5))
    db.commit()

    res = client.get(
        "/api/reportes/balance-masa", params={"n_declaracion": "9999999"}, headers=_auth(client, usuario_admin)
    )
    assert res.status_code == 200
    filas = res.json()
    assert len(filas) == 1
    assert filas[0]["n_declaracion"] == "9999999"
    assert filas[0]["materia_prima_ton"] == 2.0
    assert filas[0]["producto_ton"] == 1.5


def _auth(client, usuario) -> dict:
    from app.auth import crear_token

    return {"Authorization": f"Bearer {crear_token(usuario.id)}"}
