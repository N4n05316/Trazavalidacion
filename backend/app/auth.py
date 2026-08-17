"""
Login con correo + contraseña, gestionado por un administrador (sin
autoregistro). La sesión se guarda en una cookie firmada (SessionMiddleware).

Se eligió esto (en vez de login social) porque el correo corporativo de
Friosur es Microsoft/Outlook, y no había garantía de que el tenant de Azure
AD de la empresa permitiera el consentimiento de una app externa — para un
equipo chico, contraseñas administradas directamente evitan esa dependencia.
"""
from __future__ import annotations

import uuid

import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rol, Usuario


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="No autenticado")
    usuario = db.get(Usuario, uuid.UUID(user_id))
    if usuario is None or not usuario.activo:
        request.session.clear()
        raise HTTPException(status_code=401, detail="No autenticado")
    return usuario


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Usuario | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(Usuario, uuid.UUID(user_id))


def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.rol != Rol.ADMIN:
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    return usuario
