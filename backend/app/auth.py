"""
Login con correo + contraseña, gestionado por un administrador (sin
autoregistro). La sesión se identifica con un JWT firmado (no una cookie).

Se eligió correo/contraseña (en vez de login social) porque el correo
corporativo de Friosur es Microsoft/Outlook, y no había garantía de que el
tenant de Azure AD de la empresa permitiera el consentimiento de una app
externa — para un equipo chico, contraseñas administradas directamente
evitan esa dependencia.

Se usa JWT en vez de cookie de sesión porque en producción el frontend
(GitHub Pages) y el backend (Render) viven en dominios completamente
distintos — la cookie de sesión queda clasificada como "de terceros" por
el navegador, y cada vez más navegadores las bloquean por defecto incluso
con SameSite=None + Secure bien configurado. Un token que el propio
frontend guarda y reenvía en el header Authorization no depende de esa
política del navegador.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Rol, Usuario

JWT_ALGORITHM = "HS256"
JWT_EXPIRA_DIAS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def crear_token(usuario_id: uuid.UUID) -> str:
    payload = {
        "sub": str(usuario_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRA_DIAS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.session_secret, algorithm=JWT_ALGORITHM)


def _decodificar_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.session_secret, algorithms=[JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def _extraer_token(request: Request, token_qs: str | None) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    # Fallback vía query param — necesario para links de descarga directa
    # (<a href>, PDF/Excel) que no pueden llevar headers custom.
    return token_qs


def get_current_user(
    request: Request, db: Session = Depends(get_db), token: str | None = Query(default=None)
) -> Usuario:
    raw_token = _extraer_token(request, token)
    user_id = _decodificar_token(raw_token) if raw_token else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    usuario = db.get(Usuario, user_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=401, detail="No autenticado")
    return usuario


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db), token: str | None = Query(default=None)
) -> Usuario | None:
    raw_token = _extraer_token(request, token)
    user_id = _decodificar_token(raw_token) if raw_token else None
    if user_id is None:
        return None
    usuario = db.get(Usuario, user_id)
    if usuario is None or not usuario.activo:
        return None
    return usuario


def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.rol != Rol.ADMIN:
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    return usuario
