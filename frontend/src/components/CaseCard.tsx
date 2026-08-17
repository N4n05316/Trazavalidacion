import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import { useState } from "react";
import { api, facsimilUrl } from "../api/client";
import type { Caso, EstadoRevision, Linea } from "../api/types";
import { Seal } from "./Seal";
import { RevisionBadge } from "./RevisionBadge";

const ESTADOS: EstadoRevision[] = ["PENDIENTE", "CONFIRMADO ERROR", "FALSO POSITIVO"];

/**
 * DI con más líneas para este lote — el origen "esperado". Ignora líneas sin
 * DI resuelto (cadena de producción propia no trazada hasta un DI directo en
 * esta declaración): no son inconsistentes, simplemente no hay con qué
 * compararlas.
 */
function diDominante(lineas: Linea[]): string {
  const conteo: Record<string, number> = {};
  for (const l of lineas) {
    if (!l.di) continue;
    conteo[l.di] = (conteo[l.di] ?? 0) + 1;
  }
  return Object.entries(conteo).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
}

export function CaseCard({ caso, onUpdated }: { caso: Caso; onUpdated: () => void }) {
  const [open, setOpen] = useState(false);
  const [lineas, setLineas] = useState<Linea[] | null>(null);
  const [loadingLineas, setLoadingLineas] = useState(false);
  const [savingNotas, setSavingNotas] = useState(false);
  const [notas, setNotas] = useState(caso.notas);

  const dis = caso.di_asociados ? caso.di_asociados.split(", ").filter(Boolean) : [];
  const agentes = caso.agentes ? caso.agentes.split(", ").filter(Boolean) : [];

  const toggleOpen = async () => {
    const next = !open;
    setOpen(next);
    if (next && lineas === null) {
      setLoadingLineas(true);
      try {
        setLineas(await api.incumplimientos(false, caso.lote));
      } finally {
        setLoadingLineas(false);
      }
    }
  };

  const cambiarEstado = async (estado: EstadoRevision) => {
    await api.actualizarCaso(caso.id, { estado_revision: estado });
    onUpdated();
  };

  const guardarNotas = async () => {
    setSavingNotas(true);
    try {
      await api.actualizarCaso(caso.id, { notas });
    } finally {
      setSavingNotas(false);
    }
  };

  return (
    <div className="case-card">
      <div className="case-head">
        <Seal status="revisar" size={52} />
        <div className="case-head-text">
          <div className="case-title">
            Lote <span className="mono">{caso.lote}</span>
            <RevisionBadge status={caso.estado_revision} />
          </div>
          <div className="case-sub">
            {caso.n_declaraciones} declaraciones involucradas — agente(s) {agentes.join(", ") || "?"}.
          </div>
        </div>
        <div className="case-di-pills">
          {dis.map((d) => (
            <span key={d} className="pill pill--warn">
              DI {d}
            </span>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
        <span className="dim" style={{ fontSize: 11.5 }}>
          Estado de revisión:
        </span>
        <select value={caso.estado_revision} onChange={(e) => cambiarEstado(e.target.value as EstadoRevision)}>
          {ESTADOS.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
        <input
          type="text"
          placeholder="Notas de revisión…"
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          style={{ flex: 1 }}
        />
        <button className="btn btn-ghost" disabled={savingNotas || notas === caso.notas} onClick={guardarNotas}>
          Guardar
        </button>
      </div>

      <button className="expand-btn" onClick={toggleOpen}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {open ? "Ocultar declaraciones" : "Ver declaraciones con inconsistencia"}
      </button>

      {open && (
        <div style={{ marginTop: 10 }}>
          {loadingLineas && <div className="dim" style={{ fontSize: 12, padding: 8 }}>Cargando…</div>}
          {lineas &&
            (() => {
              const esperado = diDominante(lineas);
              const inconsistentes = lineas.filter((l) => l.di && l.di !== esperado);
              return (
                <>
                  <p className="dim" style={{ fontSize: 11.5, marginBottom: 8 }}>
                    DI esperado (mayoritario): <span className="mono">{esperado || "—"}</span> — {inconsistentes.length} de{" "}
                    {lineas.length} declaraciones tienen un DI distinto (las demás, sin DI resuelto en esta línea, no se
                    muestran aquí).
                  </p>
                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Declaración</th>
                          <th>DI</th>
                          <th>Agente</th>
                          <th>Especie</th>
                          <th>Producto</th>
                          <th>Fecha</th>
                          <th className="num">Ton.</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {inconsistentes.map((l) => (
                          <tr key={l.id}>
                            <td className="mono">{l.n_declaracion}</td>
                            <td className="mono" style={{ color: "var(--warn)" }}>
                              {l.di}
                            </td>
                            <td className="dim">{l.agente}</td>
                            <td>{l.especie}</td>
                            <td className="dim">{l.producto}</td>
                            <td className="mono dim">{l.fecha_declaracion}</td>
                            <td className="num mono">{l.toneladas}</td>
                            <td>
                              <a
                                href={facsimilUrl(l.n_declaracion)}
                                target="_blank"
                                rel="noreferrer"
                                title="Ver facsímil PDF de esta declaración"
                                style={{ color: "var(--brass)", display: "inline-flex" }}
                              >
                                <FileText size={14} />
                              </a>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              );
            })()}
        </div>
      )}
    </div>
  );
}
