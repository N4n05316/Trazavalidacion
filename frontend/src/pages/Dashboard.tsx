import { useEffect, useMemo, useState } from "react";
import { Anchor, CircleHelp, Fish, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { Caso, Ejecucion, ResumenEjecutivo } from "../api/types";
import { KpiCard } from "../components/KpiCard";
import { Seal } from "../components/Seal";
import { CenterMessage } from "../components/CenterMessage";
import { CaseCard } from "../components/CaseCard";

const COLORS = { brass: "#c9974d", brassSoft: "#8a6a3a", line: "#1d4451", panelAlt: "#0f2733", text: "#eaf1f0", textDim: "#8fa9ab" };

function shortName(n: string) {
  return n.length > 22 ? n.slice(0, 20) + "…" : n;
}

export function Dashboard() {
  const [resumen, setResumen] = useState<ResumenEjecutivo | null>(null);
  const [casos, setCasos] = useState<Caso[]>([]);
  const [ultimaEjecucion, setUltimaEjecucion] = useState<Ejecucion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, c, ejecs] = await Promise.all([api.resumen(), api.casos("PENDIENTE"), api.ejecuciones()]);
      setResumen(r);
      setCasos(c);
      setUltimaEjecucion(ejecs[0] ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const chartData = useMemo(
    () => (resumen ? resumen.especies.map((e) => ({ name: shortName(e.especie), ton: e.toneladas })) : []),
    [resumen]
  );

  if (loading && !resumen) {
    return <CenterMessage icon={RefreshCw} title="Cargando resumen…">Consultando la base de datos.</CenterMessage>;
  }
  if (error) {
    return (
      <CenterMessage icon={TriangleAlert} title="No se pudo cargar el resumen">
        {error} <button className="btn" style={{ marginLeft: 8 }} onClick={load}>Reintentar</button>
      </CenterMessage>
    );
  }
  if (!resumen) return null;

  const pctOk = Math.round(((resumen.lotes_ok + resumen.lotes_ok_parcial) / Math.max(resumen.total_lotes, 1)) * 100);

  return (
    <>
      <section
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          paddingBottom: 36,
          marginBottom: 28,
          borderBottom: "1px solid var(--line)",
          gap: 24,
          flexWrap: "wrap",
        }}
      >
        <div>
          <span style={{ fontSize: 11.5, letterSpacing: 1.6, textTransform: "uppercase", color: COLORS.brass, fontWeight: 600 }}>
            Auditoría de trazabilidad · acumulado
          </span>
          <h1 style={{ fontFamily: "Spectral, serif", fontWeight: 600, fontSize: 32, lineHeight: 1.15, margin: "10px 0 14px" }}>
            {pctOk}% de los lotes calzan
            <br />
            limpio con su DI de origen
          </h1>
          <p style={{ color: "var(--text-dim)", fontSize: 14, maxWidth: 460, lineHeight: 1.55 }}>
            Sobre {resumen.total_lotes} lotes con nacimiento directo desde un Documento de Desembarque,
            validados por balance de toneladas, no por orden de filas del reporte.
          </p>
          {ultimaEjecucion && (
            <p className="dim mono" style={{ fontSize: 11.5, marginTop: 10 }}>
              Última corrida: {new Date(ultimaEjecucion.fecha_ejecucion).toLocaleString("es-CL")} — {ultimaEjecucion.archivo_nombre}
            </p>
          )}
        </div>
        <Seal status={resumen.lotes_revisar === 0 ? "ok" : "revisar"} size={104} />
      </section>

      <section className="kpi-grid">
        <KpiCard icon={ShieldCheck} label="Lotes OK" value={resumen.lotes_ok} tone="ok" sub="Un solo DI de origen" />
        <KpiCard icon={Anchor} label="OK · DI parcial + definitivo" value={resumen.lotes_ok_parcial} tone="brass" sub="Mismo barco, dos declaraciones" />
        <KpiCard icon={TriangleAlert} label="A revisar" value={resumen.lotes_revisar} tone="warn" sub="DI de barcos distintos" />
        <KpiCard icon={CircleHelp} label="Casos pendientes" value={casos.length} tone="unk" sub="Sin resolución manual aún" />
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 14, marginBottom: 36 }}>
        <div className="panel">
          <div className="panel-title">
            <Fish size={15} strokeWidth={1.8} />
            Toneladas trazadas por especie
          </div>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
              <CartesianGrid horizontal={false} stroke={COLORS.line} strokeDasharray="2 4" />
              <XAxis type="number" tick={{ fill: COLORS.textDim, fontSize: 11 }} axisLine={{ stroke: COLORS.line }} tickLine={false} />
              <YAxis type="category" dataKey="name" width={150} tick={{ fill: COLORS.text, fontSize: 11.5 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}`, borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: COLORS.text }}
                itemStyle={{ color: COLORS.brass }}
                formatter={(v: number) => [`${v} ton`, "Trazado"]}
              />
              <Bar dataKey="ton" radius={[0, 3, 3, 0]} barSize={14}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={i === 0 ? COLORS.brass : COLORS.brassSoft} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <div className="panel-title">
            <ShieldCheck size={15} strokeWidth={1.8} />
            Cómo se valida
          </div>
          <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, color: "var(--text-dim)", lineHeight: 1.7 }}>
            <li>
              <b style={{ color: "var(--text)" }}>1. Balance de toneladas.</b> Los kg declarados de un DI deben calzar con los kg de
              producto + desecho que resultan de él.
            </li>
            <li>
              <b style={{ color: "var(--text)" }}>2. Fusión de líneas de un mismo DI.</b> Cuando un DI se declara en dos líneas para
              el mismo origen/especie, se suman antes de buscar el calce.
            </li>
            <li>
              <b style={{ color: "var(--text)" }}>3. Regla del barco.</b> Un lote puede tener 2 DI solo si son del mismo agente/barco
              (parcial + definitivo).
            </li>
          </ol>
        </div>
      </section>

      <section className="cases-section">
        <div className="section-heading">
          <TriangleAlert size={16} color="#c1594c" strokeWidth={1.8} />
          <h2>Casos pendientes de revisión</h2>
          <span className="section-count">{casos.length}</span>
        </div>
        {casos.length === 0 ? (
          <div className="panel" style={{ color: "var(--text-dim)", fontSize: 13 }}>
            No hay casos pendientes de revisión.
          </div>
        ) : (
          <div className="cases-grid">
            {casos.slice(0, 5).map((c) => (
              <CaseCard key={c.id} caso={c} onUpdated={load} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
