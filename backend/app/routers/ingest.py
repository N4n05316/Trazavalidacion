from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import IngestResult
from app.services.ingestion import ArchivoYaProcesadoError, ingest_reporte_produccion
from app.services.materia_prima_externa import ingest_trazabilidad_externa

router = APIRouter(prefix="/api/ingest", tags=["ingesta"])


@router.post("/produccion", response_model=IngestResult)
async def subir_reporte_produccion(archivo: UploadFile, db: Session = Depends(get_db)):
    raw = await archivo.read()
    try:
        ejecucion = ingest_reporte_produccion(db, raw, archivo.filename)
    except ArchivoYaProcesadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return IngestResult(
        ejecucion=ejecucion,
        lotes_ok=ejecucion.lotes_ok,
        lotes_ok_parcial=ejecucion.lotes_ok_parcial,
        lotes_revisar=ejecucion.lotes_revisar,
        lotes_sin_determinar=ejecucion.lotes_sin_determinar,
    )


@router.post("/trazabilidad")
async def subir_trazabilidad_interna(archivo: UploadFile, db: Session = Depends(get_db)):
    raw = await archivo.read()
    try:
        agregadas = ingest_trazabilidad_externa(db, raw, archivo.filename)
    except ArchivoYaProcesadoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"filas_nuevas": agregadas}
