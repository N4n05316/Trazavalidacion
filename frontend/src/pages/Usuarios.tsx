import { useEffect, useState, type FormEvent } from "react";
import { RefreshCw, UserPlus, Users as UsersIcon } from "lucide-react";
import { ApiError, api } from "../api/client";
import type { Rol, Usuario } from "../api/types";
import { CenterMessage } from "../components/CenterMessage";

function NuevoUsuarioForm({ onCreado }: { onCreado: () => void }) {
  const [email, setEmail] = useState("");
  const [nombre, setNombre] = useState("");
  const [password, setPassword] = useState("");
  const [rol, setRol] = useState<Rol>("operador");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await api.crearUsuario({ email: email.trim(), nombre: nombre.trim(), password, rol });
      setEmail("");
      setNombre("");
      setPassword("");
      setRol("operador");
      onCreado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="panel" style={{ marginBottom: 20 }}>
      <div className="panel-title">
        <UserPlus size={15} strokeWidth={1.8} />
        Nuevo usuario
      </div>
      {error && (
        <div style={{ color: "var(--warn)", fontSize: 12, marginBottom: 12 }}>{error}</div>
      )}
      <div className="field-row" style={{ marginBottom: 0 }}>
        <input type="text" placeholder="correo@friosur.cl" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input type="text" placeholder="Nombre completo" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <input type="password" placeholder="Contraseña temporal" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <select value={rol} onChange={(e) => setRol(e.target.value as Rol)}>
          <option value="operador">Operador</option>
          <option value="admin">Admin</option>
        </select>
        <button className="btn" type="submit" disabled={enviando}>
          Crear
        </button>
      </div>
    </form>
  );
}

export function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      setUsuarios(await api.usuarios());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggleActivo = async (u: Usuario) => {
    await api.actualizarUsuario(u.id, { activo: !u.activo });
    load();
  };

  const cambiarRol = async (u: Usuario, rol: Rol) => {
    await api.actualizarUsuario(u.id, { rol });
    load();
  };

  return (
    <>
      <div className="page-heading">
        <UsersIcon size={20} color="#c9974d" strokeWidth={1.8} />
        <h1>Usuarios</h1>
      </div>
      <p className="page-sub">Gestión de cuentas — solo visible para administradores.</p>

      <NuevoUsuarioForm onCreado={load} />

      {error && <CenterMessage icon={RefreshCw} title="Error">{error}</CenterMessage>}

      {usuarios && (
        <div className="panel">
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Correo</th>
                  <th>Nombre</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th>Último login</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => (
                  <tr key={u.id}>
                    <td className="mono">{u.email}</td>
                    <td>{u.nombre}</td>
                    <td>
                      <select value={u.rol} onChange={(e) => cambiarRol(u, e.target.value as Rol)}>
                        <option value="operador">Operador</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td>
                      <span className={"pill " + (u.activo ? "pill--ok" : "pill--warn")}>
                        {u.activo ? "Activo" : "Deshabilitado"}
                      </span>
                    </td>
                    <td className="dim mono">{u.ultimo_login ? new Date(u.ultimo_login).toLocaleString("es-CL") : "—"}</td>
                    <td>
                      <button className="btn btn-ghost" onClick={() => toggleActivo(u)}>
                        {u.activo ? "Deshabilitar" : "Habilitar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
