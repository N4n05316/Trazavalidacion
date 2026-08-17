import type {
  BalanceMasaFila,
  Caso,
  CruceLoteDi,
  Ejecucion,
  EstadoRevision,
  IngestResult,
  Linea,
  MeResponse,
  ProductividadDiaria,
  ResumenEjecutivo,
  Rol,
  Usuario,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8010";
const TOKEN_KEY = "certus_token";

// El backend vive en un dominio distinto al frontend en producción (GitHub
// Pages + Render) — una cookie de sesión ahí queda clasificada "de terceros"
// y muchos navegadores la bloquean por defecto. En vez de depender de eso,
// el token se guarda acá y se reenvía explícitamente en cada request.
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders() },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // sin cuerpo JSON
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),

  resumen: () => request<ResumenEjecutivo>("/api/reportes/resumen"),

  casos: (estadoRevision?: EstadoRevision) =>
    request<Caso[]>(`/api/casos${estadoRevision ? `?estado_revision=${encodeURIComponent(estadoRevision)}` : ""}`),

  actualizarCaso: (id: string, payload: { estado_revision?: EstadoRevision; notas?: string }) =>
    request<Caso>(`/api/casos/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  incumplimientos: (soloRevisar: boolean, lote?: string) =>
    request<Linea[]>(
      `/api/reportes/incumplimientos?solo_revisar=${soloRevisar}${lote ? `&lote=${encodeURIComponent(lote)}` : ""}`
    ),

  balanceMasa: (params: { di?: string; lote?: string; n_declaracion?: string }) => {
    const qs = new URLSearchParams();
    if (params.di) qs.set("di", params.di);
    if (params.lote) qs.set("lote", params.lote);
    if (params.n_declaracion) qs.set("n_declaracion", params.n_declaracion);
    return request<BalanceMasaFila[]>(`/api/reportes/balance-masa?${qs.toString()}`);
  },

  declaraciones: (params?: { desde?: string; hasta?: string }) => {
    const qs = new URLSearchParams();
    if (params?.desde) qs.set("desde", params.desde);
    if (params?.hasta) qs.set("hasta", params.hasta);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<ProductividadDiaria[]>(`/api/reportes/declaraciones${suffix}`);
  },

  cruceLoteDi: () => request<CruceLoteDi[]>("/api/reportes/cruce-lote-di"),

  ejecuciones: () => request<Ejecucion[]>("/api/reportes/ejecuciones"),

  subirProduccion: async (archivo: File): Promise<IngestResult> => {
    const form = new FormData();
    form.append("archivo", archivo);
    const res = await fetch(`${BASE_URL}/api/ingest/produccion`, { method: "POST", body: form, headers: authHeaders() });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? res.statusText);
    }
    return res.json();
  },

  subirTrazabilidad: async (archivo: File): Promise<{ filas_nuevas: number }> => {
    const form = new FormData();
    form.append("archivo", archivo);
    const res = await fetch(`${BASE_URL}/api/ingest/trazabilidad`, { method: "POST", body: form, headers: authHeaders() });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? res.statusText);
    }
    return res.json();
  },

  me: () => request<MeResponse>("/api/auth/me"),

  login: async (email: string, password: string) => {
    const res = await request<{ ok: boolean; token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(res.token);
    return res;
  },

  logout: async () => {
    try {
      await request<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
    } finally {
      clearToken();
    }
  },

  usuarios: () => request<Usuario[]>("/api/usuarios"),

  crearUsuario: (payload: { email: string; nombre: string; password: string; rol: Rol }) =>
    request<Usuario>("/api/usuarios", { method: "POST", body: JSON.stringify(payload) }),

  actualizarUsuario: (id: string, payload: { nombre?: string; rol?: Rol; activo?: boolean; password?: string }) =>
    request<Usuario>(`/api/usuarios/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};

function withToken(url: string): string {
  const token = getToken();
  if (!token) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}token=${encodeURIComponent(token)}`;
}

export function facsimilUrl(nDeclaracion: string): string {
  return withToken(`${BASE_URL}/api/reportes/facsimil/${encodeURIComponent(nDeclaracion)}.pdf`);
}

export function exportarExcelUrl(): string {
  return withToken(`${BASE_URL}/api/reportes/exportar.xlsx`);
}

export { ApiError };
