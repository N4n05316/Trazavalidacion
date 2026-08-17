import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { MeResponse } from "../api/types";

interface AuthState {
  loading: boolean;
  usuario: Extract<MeResponse, { autenticado: true }> | null;
  iniciarSesion: (email: string, password: string) => Promise<void>;
  cerrarSesion: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [usuario, setUsuario] = useState<Extract<MeResponse, { autenticado: true }> | null>(null);

  const refrescar = async () => {
    const res = await api.me();
    setUsuario(res.autenticado ? res : null);
  };

  const iniciarSesion = async (email: string, password: string) => {
    await api.login(email, password);
    await refrescar();
  };

  const cerrarSesion = async () => {
    await api.logout();
    setUsuario(null);
  };

  useEffect(() => {
    refrescar().finally(() => setLoading(false));
  }, []);

  return <AuthContext.Provider value={{ loading, usuario, iniciarSesion, cerrarSesion }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
