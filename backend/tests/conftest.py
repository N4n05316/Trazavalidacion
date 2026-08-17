"""
Fixtures compartidas. Corre contra una base de datos Postgres de test
separada (nunca la de desarrollo/producción) — se fija DATABASE_URL antes
de importar cualquier módulo de la app, porque la configuración se lee una
sola vez al importar app.config.
"""
import os
import uuid

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://certus:certus@localhost:5432/certus_test"
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Rol, Usuario  # noqa: E402

_engine = create_engine(settings.database_url)
_TestSession = sessionmaker(bind=_engine)

_TABLAS = [
    "sin_determinar", "ejecuciones", "casos", "lineas", "lineas_crudas",
    "materia_prima_externa", "productividad_diaria", "archivos_procesados", "usuarios",
]


@pytest.fixture()
def db():
    """Sesión de DB de test, limpiando todas las tablas antes de cada test para aislarlos."""
    session = _TestSession()
    for tabla in _TABLAS:
        session.execute(text(f"DELETE FROM {tabla}"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def usuario_admin(db):
    usuario = Usuario(
        id=uuid.uuid4(),
        email="admin@test.friosur.cl",
        nombre="Admin de prueba",
        password_hash=hash_password("contraseña-de-prueba"),
        rol=Rol.ADMIN,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
