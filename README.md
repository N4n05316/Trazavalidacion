# Certus — Trazabilidad Lote ↔ DI

Aplicación web para auditar automáticamente que el Lote digitado por un
operador en el sistema de Sernapesca corresponda al DI (Documento de
Desembarque Industrial) real del que se originó — usando balance de
toneladas, no el orden de las filas del reporte.

Migración de una solución previa en Google Sheets + Apps Script, validada
con datos reales de producción durante varios meses.

## Stack

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy + Alembic (`backend/`)
- **Frontend**: React + TypeScript + Vite (`frontend/`)

## Backend — desarrollo local

```bash
cd backend
python -m venv venv
venv/Scripts/activate  # Windows
pip install -r requirements.txt
cp .env.example .env   # completar con tus credenciales locales
alembic upgrade head
python scripts/crear_usuario.py --email admin@tudominio.cl --nombre "Nombre" --password "contraseña" --admin
uvicorn app.main:app --reload --port 8010
```

## Frontend — desarrollo local

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Módulos principales

- `app/services/engine.py` — motor de resolución Lote↔DI (balance de
  toneladas, fusión de líneas por DI, clasificación OK / OK-parcial / a
  revisar).
- `app/services/facsimile.py` + `pdf_facsimile.py` — reconstrucción en PDF
  de una declaración tal cual fue digitada, con el lote esperado por DI
  resaltado para comparar visualmente contra lo declarado.
- `app/routers/reportes.py` — reportes: incumplimientos, balance de masa,
  productividad diaria, cruce de 3 vías, export a Excel.
- `app/auth.py` + `app/routers/auth.py` — autenticación por correo y
  contraseña, con gestión de usuarios para administradores.
