import { useState, type FormEvent } from "react";
import { Waves } from "lucide-react";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function Login() {
  const { iniciarSesion } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await iniciarSesion(email.trim(), password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <form onSubmit={onSubmit} className="panel" style={{ maxWidth: 380, width: "100%", padding: "40px 36px" }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div className="brand-mark" style={{ width: 52, height: 52, margin: "0 auto 18px" }}>
            <Waves size={26} strokeWidth={1.6} />
          </div>
          <div className="brand-name" style={{ fontSize: 24, marginBottom: 4 }}>
            Certus
          </div>
          <div className="dim" style={{ fontSize: 12.5 }}>
            Trazabilidad Lote &harr; DI — Pesquera Friosur SpA
          </div>
        </div>

        {error && (
          <div
            style={{
              background: "rgba(193,89,76,0.14)",
              border: "1px solid rgba(193,89,76,0.4)",
              color: "var(--warn)",
              borderRadius: 8,
              padding: "10px 12px",
              fontSize: 12,
              marginBottom: 18,
            }}
          >
            {error}
          </div>
        )}

        <label style={{ display: "block", fontSize: 11.5, color: "var(--text-dim)", marginBottom: 5 }}>Correo</label>
        <input
          type="text"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoFocus
          required
          style={{ width: "100%", marginBottom: 14 }}
        />

        <label style={{ display: "block", fontSize: 11.5, color: "var(--text-dim)", marginBottom: 5 }}>Contraseña</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{ width: "100%", marginBottom: 22 }}
        />

        <button type="submit" className="btn" disabled={enviando} style={{ width: "100%", padding: "10px 0" }}>
          {enviando ? "Ingresando…" : "Iniciar sesión"}
        </button>

        <p className="dim" style={{ fontSize: 11, marginTop: 16, textAlign: "center" }}>
          ¿No tienes cuenta? Pídele acceso a un administrador de Certus.
        </p>
      </form>
    </div>
  );
}
