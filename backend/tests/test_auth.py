"""
Valida el cambio de autenticación por cookie de sesión a JWT Bearer token
(ver app/auth.py) — motivado porque frontend (GitHub Pages) y backend
(Render) viven en dominios distintos, y los navegadores bloquean cookies
de sesión "de terceros" en ese escenario.
"""
from app.auth import crear_token


def test_login_con_credenciales_correctas_devuelve_token(client, usuario_admin):
    res = client.post("/api/auth/login", json={"email": usuario_admin.email, "password": "contraseña-de-prueba"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert isinstance(body["token"], str) and len(body["token"]) > 20


def test_login_con_password_incorrecta_devuelve_401_sin_token(client, usuario_admin):
    res = client.post("/api/auth/login", json={"email": usuario_admin.email, "password": "password-equivocada"})
    assert res.status_code == 401
    assert "token" not in res.json()


def test_login_usuario_inactivo_es_rechazado(client, usuario_admin, db):
    usuario_admin.activo = False
    db.commit()
    res = client.post("/api/auth/login", json={"email": usuario_admin.email, "password": "contraseña-de-prueba"})
    assert res.status_code == 401


def test_ruta_protegida_sin_token_devuelve_401(client):
    res = client.get("/api/casos")
    assert res.status_code == 401


def test_ruta_protegida_con_token_en_header_autoriza(client, usuario_admin):
    login = client.post("/api/auth/login", json={"email": usuario_admin.email, "password": "contraseña-de-prueba"})
    token = login.json()["token"]

    res = client.get("/api/casos", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == []


def test_token_malformado_es_rechazado(client):
    res = client.get("/api/casos", headers={"Authorization": "Bearer esto-no-es-un-jwt-valido"})
    assert res.status_code == 401


def test_me_sin_token_devuelve_no_autenticado(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json() == {"autenticado": False}


def test_me_con_token_devuelve_datos_del_usuario(client, usuario_admin):
    login = client.post("/api/auth/login", json={"email": usuario_admin.email, "password": "contraseña-de-prueba"})
    token = login.json()["token"]

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    body = res.json()
    assert body["autenticado"] is True
    assert body["email"] == usuario_admin.email
    assert body["rol"] == "admin"


def test_token_via_query_param_autoriza_igual_que_header(client, usuario_admin):
    """
    Necesario para los links de descarga (facsímil PDF, export Excel) que son
    <a href> planos y no pueden llevar un header Authorization custom.
    """
    token = crear_token(usuario_admin.id)

    res = client.get(f"/api/auth/me?token={token}")
    assert res.json()["autenticado"] is True

    res_sin_token = client.get("/api/auth/me?token=token-invalido-xyz")
    assert res_sin_token.json()["autenticado"] is False
