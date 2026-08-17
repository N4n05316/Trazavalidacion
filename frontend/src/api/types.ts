export type EstadoRevision = "PENDIENTE" | "CONFIRMADO ERROR" | "FALSO POSITIVO";

export interface Ejecucion {
  id: string;
  fecha_ejecucion: string;
  archivo_nombre: string;
  lotes_ok: number;
  lotes_ok_parcial: number;
  lotes_revisar: number;
  lotes_sin_determinar: number;
}

export interface Caso {
  id: string;
  lote: string;
  fecha_detectado: string;
  di_asociados: string;
  agentes: string;
  n_declaraciones: number;
  estado_revision: EstadoRevision;
  notas: string;
}

export interface Linea {
  id: string;
  lote: string;
  tipo_linea: string;
  estado: string;
  n_declaracion: string;
  di: string;
  declaracion_origen: string;
  agente: string;
  fecha_desembarque_di: string | null;
  fecha_elaboracion_linea: string | null;
  fecha_declaracion: string | null;
  producto: string;
  especie: string;
  codigo_producto: string;
  nombre_bodega: string;
  toneladas: number;
  archivo_origen: string;
}

export interface BalanceMasaFila {
  n_declaracion: string;
  di: string;
  lote: string;
  especie: string;
  materia_prima_ton: number;
  producto_ton: number;
  desecho_ton: number;
  balance: number;
}

export interface ProductividadDiaria {
  fecha: string;
  n_declaraciones: number;
  n_lineas_totales: number;
  n_lineas_materia_prima: number;
  n_lineas_produccion: number;
  n_di_distintos: number;
  n_especies_distintas: number;
  toneladas_producto: number;
  toneladas_materia_prima: number;
}

export interface CruceLoteDi {
  lote: string;
  di_externo: string[];
  di_resuelto: string[];
  estado_cruce: string;
  estado_interno: string;
  especies: string[];
  barcos: string[];
}

export interface ResumenEjecutivo {
  lotes_ok: number;
  lotes_ok_parcial: number;
  lotes_revisar: number;
  total_lotes: number;
  especies: { especie: string; toneladas: number }[];
}

export interface IngestResult {
  ejecucion: Ejecucion;
  lotes_ok: number;
  lotes_ok_parcial: number;
  lotes_revisar: number;
  lotes_sin_determinar: number;
}

export type MeResponse =
  | { autenticado: false }
  | { autenticado: true; id: string; email: string; nombre: string; rol: string };

export type Rol = "operador" | "admin";

export interface Usuario {
  id: string;
  email: string;
  nombre: string;
  rol: Rol;
  activo: boolean;
  creado_en: string;
  ultimo_login: string | null;
}
