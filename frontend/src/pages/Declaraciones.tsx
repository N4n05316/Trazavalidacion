import { useEffect, useMemo, useState } from "react";
import { CalendarDays, RefreshCw } from "lucide-react";
import { Line, LineChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { ProductividadDiaria } from "../api/types";
import { CenterMessage } from "../components/CenterMessage";

const COLORS = { brass: "#c9974d", ok: "#5ea37b", line: "#1d4451", panelAlt: "#0f2733", text: "#eaf1f0", textDim: "#8fa9ab" };

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

function mesLabel(clave: string) {
  const [anio, mes] = clave.split("-");
  return `${MESES[parseInt(mes, 10) - 1]} ${anio}`;
}

export function Declaraciones() {
  const [datos, setDatos] = useState<ProductividadDiaria[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mes, setMes] = useState<string>("todos");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setDatos(await api.declaraciones());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const meses = useMemo(() => {
    if (!datos) return [];
    return [...new Set(datos.map((d) => d.fecha.slice(0, 7)))].sort();
  }, [datos]);

  const filtrados = useMemo(() => {
    if (!datos) return [];
    return mes === "todos" ? datos : datos.filter((d) => d.fecha.startsWith(mes));
  }, [datos, mes]);

  if (loading) return <CenterMessage icon={RefreshCw} title="Cargando productividad diaria…" />;
  if (error) return <CenterMessage icon={CalendarDays} title="Error">{error}</CenterMessage>;
  if (!datos) return null;

  return (
    <>
      <div className="page-heading">
        <CalendarDays size={20} color="#c9974d" strokeWidth={1.8} />
        <h1>Productividad diaria de digitación</h1>
      </div>
      <p className="page-sub">
        Agregado por día de declaración (no hay forma de identificar quién digitó cada línea) — cantidad de
        declaraciones, líneas, kg y DI distintos manejados por jornada.
      </p>

      <div className="field-row">
        <select value={mes} onChange={(e) => setMes(e.target.value)}>
          <option value="todos">Todos los meses</option>
          {meses.map((m) => (
            <option key={m} value={m}>
              {mesLabel(m)}
            </option>
          ))}
        </select>
      </div>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-title">Toneladas de producto y N° de declaraciones por día</div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={filtrados} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid stroke={COLORS.line} strokeDasharray="2 4" />
            <XAxis dataKey="fecha" tick={{ fill: COLORS.textDim, fontSize: 10 }} axisLine={{ stroke: COLORS.line }} tickLine={false} />
            <YAxis
              yAxisId="left"
              tick={{ fill: COLORS.textDim, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              label={{ value: "Ton. producto", angle: -90, position: "insideLeft", fill: COLORS.textDim, fontSize: 10 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: COLORS.textDim, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
              label={{ value: "N° declaraciones", angle: 90, position: "insideRight", fill: COLORS.textDim, fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}`, borderRadius: 6, fontSize: 12 }}
              labelStyle={{ color: COLORS.text }}
            />
            <Legend wrapperStyle={{ fontSize: 11.5, color: COLORS.textDim }} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="toneladas_producto"
              stroke={COLORS.brass}
              strokeWidth={2}
              dot={false}
              name="Ton. producto"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="n_declaraciones"
              stroke={COLORS.ok}
              strokeWidth={1.75}
              dot={false}
              name="N° declaraciones"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th className="num">Declaraciones</th>
                <th className="num">Líneas totales</th>
                <th className="num">Mat. Prima</th>
                <th className="num">Producción</th>
                <th className="num">DI distintos</th>
                <th className="num">Especies</th>
                <th className="num">Ton. Producto</th>
                <th className="num">Ton. Mat. Prima</th>
              </tr>
            </thead>
            <tbody>
              {[...filtrados].reverse().map((d) => (
                <tr key={d.fecha}>
                  <td className="mono">{d.fecha}</td>
                  <td className="num mono">{d.n_declaraciones}</td>
                  <td className="num mono">{d.n_lineas_totales}</td>
                  <td className="num mono">{d.n_lineas_materia_prima}</td>
                  <td className="num mono">{d.n_lineas_produccion}</td>
                  <td className="num mono">{d.n_di_distintos}</td>
                  <td className="num mono">{d.n_especies_distintas}</td>
                  <td className="num mono">{d.toneladas_producto.toFixed(3)}</td>
                  <td className="num mono">{d.toneladas_materia_prima.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
