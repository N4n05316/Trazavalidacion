from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.auth import get_current_user as require_user
from app.config import settings
from app.routers import auth, casos, ingest, reportes

app = FastAPI(title="Certus — Trazabilidad Lote↔DI", version="0.1.0")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="none" if settings.session_cookie_cross_site else "lax",
    https_only=settings.session_cookie_cross_site,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(auth.usuarios_router)
app.include_router(ingest.router, dependencies=[Depends(require_user)])
app.include_router(casos.router, dependencies=[Depends(require_user)])
app.include_router(reportes.router, dependencies=[Depends(require_user)])


@app.get("/api/health")
def health():
    return {"status": "ok"}
