import { useEffect, useMemo, useRef, useState } from "react";
import { GitCompare, RefreshCw, Search } from "lucide-react";
import { api } from "../api/client";
import type { CruceLoteDi } from "../api/types";
import { CenterMessage } from "../components/CenterMessage";

const ESTADO_CLASS: Record<string, string> = {
  "DISCREPANCIA - revisar": "pill--warn",
  "OK - coincide": "pill--ok",
};

function fmtFecha(f: string | null): string {
  if (!f) return "—";
  const [y, m, d] = f.split("-");
  return `${d}-${m}-${y}`;
}

export function Cruce() {
  const [filas, setFilas] = useState<CruceLoteDi[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [soloDiscrepancias, setSoloDiscrepancias] = useState(false);
  const [estadoInterno, setEstadoInterno] = useState<string>("todos");
  const [busqueda, setBusqueda] = useState("");
  const [resaltado, setResaltado] = useState<string | null>(null);
  const [busquedaError, setBusquedaError] = useState(false);
  const filaRefs = useRef<Record<string, HTMLTableRowElement | null>>({});

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setFilas(await api.cruceLoteDi());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const estadosInternos = useMemo(() => {
    if (!filas) return [];
    return [...new Set(filas.map((f) => f.estado_interno).filter(Boolean))].sort();
  }, [filas]);

  if (loading) return <CenterMessage icon={RefreshCw} title="Calculando cruce…" />;
  if (error) return <CenterMessage icon={GitCompare} title="Error">{error}</CenterMessage>;
  if (!filas) return null;

  const visibles = filas.filter(
    (f) =>
      (!soloDiscrepancias || f.estado_cruce === "DISCREPANCIA - revisar") &&
      (estadoInterno === "todos" || f.estado_interno === estadoInterno)
  );

  const irABusqueda = () => {
    const q = busqueda.trim();
    if (!q) return;
    const match = visibles.find(
      (f) => f.lote === q || f.di_externo.includes(q) || f.di_resuelto.includes(q)
    );
    if (!match) {
      setBusquedaError(true);
      setResaltado(null);
      return;
    }
    setBusquedaError(false);
    setResaltado(match.lote);
    filaRefs.current[match.lote]?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <>
      <div className="page-heading">
        <GitCompare size={20} color="#c9974d" strokeWidth={1.8} />
        <h1>Cruce Lote-DI (3 vías)</h1>
      </div>
      <p className="page-sub">
        Compara el registro interno de la planta, el lote digitado en Sernapesca, y el DI resuelto por el
        algoritmo de balance de toneladas. Ordenado del lote más reciente al más antiguo.
      </p>

      <div className="field-row">
        <button className={"btn" + (soloDiscrepancias ? "" : " btn-ghost")} onClick={() => setSoloDiscrepancias((v) => !v)}>
          {soloDiscrepancias ? "Mostrando solo discrepancias" : "Mostrar solo discrepancias"}
        </button>
        <select value={estadoInterno} onChange={(e) => setEstadoInterno(e.target.value)}>
          <option value="todos">Todos los estados internos</option>
          {estadosInternos.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
        <button className="btn btn-ghost" onClick={load} title="Refrescar">
          <RefreshCw size={13} />
        </button>
      </div>

      <div className="field-row">
        <input
          type="text"
          placeholder="Ir a un Lote o DI…"
          value={busqueda}
          onChange={(e) => {
            setBusqueda(e.target.value);
            setBusquedaError(false);
          }}
          onKeyDown={(e) => e.key === "Enter" && irABusqueda()}
        />
        <button className="btn" onClick={irABusqueda} disabled={!busqueda.trim()}>
          <Search size={13} /> Ir
        </button>
        {busquedaError && (
          <span style={{ color: "var(--warn)", fontSize: 13 }}>
            No se encontró ese Lote/DI (con los filtros actuales).
          </span>
        )}
      </div>

      <div className="panel">
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Lote</th>
                <th>DI externo (interno)</th>
                <th>DI resuelto (Sernapesca)</th>
                <th>Estado del cruce</th>
                <th>Estado interno</th>
                <th>Especies</th>
                <th>Barco(s)</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((f) => (
                <tr
                  key={f.lote}
                  ref={(el) => {
                    filaRefs.current[f.lote] = el;
                  }}
                  style={resaltado === f.lote ? { outline: "2px solid var(--brass)", outlineOffset: -2 } : undefined}
                >
                  <td className="dim">{fmtFecha(f.fecha)}</td>
                  <td className="mono">{f.lote}</td>
                  <td className="mono">{f.di_externo.join(", ") || "—"}</td>
                  <td className="mono">{f.di_resuelto.join(", ") || "—"}</td>
                  <td>
                    <span className={"pill " + (ESTADO_CLASS[f.estado_cruce] ?? "")}>{f.estado_cruce}</span>
                  </td>
                  <td className="dim">{f.estado_interno || "—"}</td>
                  <td className="dim">{f.especies.join(", ")}</td>
                  <td className="dim">{f.barcos.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
