from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://certus:certus@localhost:5432/certus"
    tolerancia_balance_ton: float = 0.006  # TOL en Codigo.gs — tolerancia de redondeo de la plataforma Sernapesca

    session_secret: str = "change-me"
    allowed_email_domain: str = ""  # ej. "friosur.cl" — vacío = no restringe dominio al crear cuentas

    # Orígenes permitidos para CORS, separados por coma (frontend local + GitHub Pages, etc.)
    frontend_url: str = "http://localhost:5173"

    # En producción, frontend y backend viven en dominios distintos (no solo puertos
    # distintos como en dev) — ahí la cookie de sesión necesita SameSite=None + Secure
    # para que el navegador la envíe en requests cross-origin. En dev local, Lax +
    # sin Secure es lo correcto (no hay HTTPS). Se activa con SESSION_COOKIE_CROSS_SITE=true.
    session_cookie_cross_site: bool = False

    class Config:
        env_file = ".env"

    @property
    def frontend_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_url.split(",") if o.strip()]


settings = Settings()
