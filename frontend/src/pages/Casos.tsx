import { useEffect, useState } from "react";
import { RefreshCw, TriangleAlert } from "lucide-react";
import { api } from "../api/client";
import type { Caso, EstadoRevision } from "../api/types";
import { CaseCard } from "../components/CaseCard";
import { CenterMessage } from "../components/CenterMessage";

const FILTROS: { value: EstadoRevision | "TODOS"; label: string }[] = [
  { value: "TODOS", label: "Todos" },
  { value: "PENDIENTE", label: "Pendiente" },
  { value: "CONFIRMADO ERROR", label: "Confirmado error" },
  { value: "FALSO POSITIVO", label: "Falso positivo" },
];

export function Casos() {
  const [casos, setCasos] = useState<Caso[]>([]);
  const [filtro, setFiltro] = useState<EstadoRevision | "TODOS">("TODOS");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setCasos(await api.casos(filtro === "TODOS" ? undefined : filtro));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtro]);

  return (
    <>
      <div className="page-heading">
        <TriangleAlert size={20} color="#c1594c" strokeWidth={1.8} />
        <h1>Reporte de incumplimientos</h1>
      </div>
      <p className="page-sub">
        Lotes marcados a revisar (DI de barcos distintos), con su detalle de declaraciones y estado de revisión
        manual. Filtra por estado o expande un caso para ver las declaraciones involucradas.
      </p>

      <div className="field-row">
        {FILTROS.map((f) => (
          <button
            key={f.value}
            className={"btn" + (filtro === f.value ? "" : " btn-ghost")}
            onClick={() => setFiltro(f.value)}
          >
            {f.label}
          </button>
        ))}
        <button className="btn btn-ghost" onClick={load} title="Refrescar">
          <RefreshCw size={13} />
        </button>
      </div>

      {loading && <CenterMessage icon={RefreshCw} title="Cargando casos…" />}
      {error && <CenterMessage icon={TriangleAlert} title="Error">{error}</CenterMessage>}
      {!loading && !error && casos.length === 0 && (
        <div className="panel" style={{ color: "var(--text-dim)", fontSize: 13 }}>
          No hay casos con este filtro.
        </div>
      )}
      {!loading && !error && casos.length > 0 && (
        <div className="cases-grid">
          {casos.map((c) => (
            <CaseCard key={c.id} caso={c} onUpdated={load} />
          ))}
        </div>
      )}
    </>
  );
}
