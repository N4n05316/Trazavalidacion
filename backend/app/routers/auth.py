import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import crear_token, get_current_user_optional, hash_password, require_admin, verify_password
from app.config import settings
from app.database import get_db
from app.models import Usuario
from app.schemas import LoginRequest, UsuarioCreate, UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    usuario = db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()
    if usuario is None or not usuario.activo or not verify_password(payload.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    usuario.ultimo_login = datetime.utcnow()
    db.commit()

    return {"ok": True, "token": crear_token(usuario.id)}


@router.post("/logout")
def logout():
    # El token es stateless (JWT) — "cerrar sesión" es responsabilidad del
    # cliente, que simplemente lo descarta. Se mantiene el endpoint por
    # compatibilidad con el flujo del frontend.
    return {"ok": True}


@router.get("/me")
def me(usuario: Usuario | None = Depends(get_current_user_optional)):
    if usuario is None:
        return {"autenticado": False}
    return {
        "autenticado": True,
        "id": str(usuario.id),
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
    }


# ======================= Gestión de usuarios (solo admin) =======================
usuarios_router = APIRouter(prefix="/api/usuarios", tags=["usuarios"], dependencies=[Depends(require_admin)])


@usuarios_router.get("", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.execute(select(Usuario).order_by(Usuario.creado_en)).scalars().all()


@usuarios_router.post("", response_model=UsuarioOut)
def crear_usuario(payload: UsuarioCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if settings.allowed_email_domain and not email.endswith(f"@{settings.allowed_email_domain.lower()}"):
        raise HTTPException(status_code=422, detail=f"El correo debe pertenecer al dominio {settings.allowed_email_domain}")
    if db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")

    usuario = Usuario(email=email, nombre=payload.nombre, password_hash=hash_password(payload.password), rol=payload.rol)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@usuarios_router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(usuario_id: uuid.UUID, payload: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if payload.nombre is not None:
        usuario.nombre = payload.nombre
    if payload.rol is not None:
        usuario.rol = payload.rol
    if payload.activo is not None:
        usuario.activo = payload.activo
    if payload.password:
        usuario.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(usuario)
    return usuario
