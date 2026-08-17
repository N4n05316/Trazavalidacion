"""
Crea un usuario directamente en la base de datos — pensado para dar de alta
al primer administrador (el resto de las cuentas se crean después desde la
propia app, en Usuarios, una vez que ya hay un admin logueado).

Uso:
    python scripts/crear_usuario.py --email admin@friosur.cl --nombre "Nombre Apellido" --password "contraseña-temporal" --admin
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Rol, Usuario  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--admin", action="store_true", help="Crear con rol admin (por defecto: operador)")
    args = parser.parse_args()

    email = args.email.strip().lower()
    db = SessionLocal()
    try:
        if db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none():
            print(f"Ya existe un usuario con el correo {email}.")
            return
        usuario = Usuario(
            email=email,
            nombre=args.nombre,
            password_hash=hash_password(args.password),
            rol=Rol.ADMIN if args.admin else Rol.OPERADOR,
        )
        db.add(usuario)
        db.commit()
        print(f"Usuario creado: {email} ({'admin' if args.admin else 'operador'})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
