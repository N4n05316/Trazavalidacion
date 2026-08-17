import { useState } from "react";
import { FileText, RefreshCw, Scale } from "lucide-react";
import { api, facsimilUrl } from "../api/client";
import type { BalanceMasaFila } from "../api/types";
import { CenterMessage } from "../components/CenterMessage";

const TOL = 0.006;

export function BalanceMasa() {
  const [modo, setModo] = useState<"di" | "lote">("di");
  const [valor, setValor] = useState("");
  const [filas, setFilas] = useState<BalanceMasaFila[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buscar = async () => {
    if (!valor.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.balanceMasa(modo === "di" ? { di: valor.trim() } : { lote: valor.trim() });
      setFilas(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  const totales = filas?.reduce(
    (acc, f) => ({
      mp: acc.mp + f.materia_prima_ton,
      prod: acc.prod + f.producto_ton,
      desecho: acc.desecho + f.desecho_ton,
      balance: acc.balance + f.balance,
    }),
    { mp: 0, prod: 0, desecho: 0, balance: 0 }
  );

  return (
    <>
      <div className="page-heading">
        <Scale size={20} color="#c9974d" strokeWidth={1.8} />
        <h1>Balance de masa por DI o Lote</h1>
      </div>
      <p className="page-sub">
        Muestra, para cada declaración involucrada, cuánta materia prima entró vs. cuánto producto + desecho
        resultó — la misma comparación que hace el algoritmo de balance de toneladas, expuesta de forma
        transparente.
      </p>

      <div className="field-row">
        <select value={modo} onChange={(e) => setModo(e.target.value as "di" | "lote")}>
          <option value="di">Buscar por DI</option>
          <option value="lote">Buscar por Lote</option>
        </select>
        <input
          type="text"
          placeholder={modo === "di" ? "N° de DI…" : "N° de Lote…"}
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && buscar()}
        />
        <button className="btn" onClick={buscar} disabled={loading || !valor.trim()}>
          Buscar
        </button>
      </div>

      {loading && <CenterMessage icon={RefreshCw} title="Calculando balance…" />}
      {error && <CenterMessage icon={Scale} title="Error">{error}</CenterMessage>}

      {filas && filas.length === 0 && (
        <div className="panel" style={{ color: "var(--text-dim)", fontSize: 13 }}>
          No se encontraron líneas para ese {modo === "di" ? "DI" : "lote"}.
        </div>
      )}

      {filas && filas.length > 0 && (
        <div className="panel">
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Declaración</th>
                  <th>DI</th>
                  <th>Lote</th>
                  <th>Especie</th>
                  <th className="num">Materia Prima (ton)</th>
                  <th className="num">Producto (ton)</th>
                  <th className="num">Desecho (ton)</th>
                  <th className="num">Balance</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f, i) => (
                  <tr key={i}>
                    <td className="mono">{f.n_declaracion}</td>
                    <td className="mono">{f.di}</td>
                    <td className="mono">{f.lote || "—"}</td>
                    <td>{f.especie}</td>
                    <td className="num mono">{f.materia_prima_ton.toFixed(3)}</td>
                    <td className="num mono">{f.producto_ton.toFixed(3)}</td>
                    <td className="num mono">{f.desecho_ton.toFixed(3)}</td>
                    <td className={"num mono" + (Math.abs(f.balance) > TOL ? " balance-off" : "")}>
                      {f.balance.toFixed(3)}
                    </td>
                    <td>
                      <a
                        href={facsimilUrl(f.n_declaracion)}
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
              {totales && (
                <tfoot>
                  <tr style={{ fontWeight: 600 }}>
                    <td colSpan={4}>Total</td>
                    <td className="num mono">{totales.mp.toFixed(3)}</td>
                    <td className="num mono">{totales.prod.toFixed(3)}</td>
                    <td className="num mono">{totales.desecho.toFixed(3)}</td>
                    <td className={"num mono" + (Math.abs(totales.balance) > TOL ? " balance-off" : "")}>
                      {totales.balance.toFixed(3)}
                    </td>
                    <td></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      )}
    </>
  );
}
