import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Caso, EstadoRevision
from app.schemas import CasoOut, CasoUpdate

router = APIRouter(prefix="/api/casos", tags=["casos"])


@router.get("", response_model=list[CasoOut])
def listar_casos(estado_revision: EstadoRevision | None = None, db: Session = Depends(get_db)):
    stmt = select(Caso).order_by(Caso.fecha_detectado.desc())
    if estado_revision:
        stmt = stmt.where(Caso.estado_revision == estado_revision)
    return db.execute(stmt).scalars().all()


@router.patch("/{caso_id}", response_model=CasoOut)
def actualizar_caso(caso_id: uuid.UUID, payload: CasoUpdate, db: Session = Depends(get_db)):
    caso = db.get(Caso, caso_id)
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    if payload.estado_revision is not None:
        caso.estado_revision = payload.estado_revision
    if payload.notas is not None:
        caso.notas = payload.notas
    db.commit()
    db.refresh(caso)
    return caso
