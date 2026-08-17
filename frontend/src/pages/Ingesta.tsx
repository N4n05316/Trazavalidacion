import { useRef, useState } from "react";
import { CheckCircle2, UploadCloud, XCircle } from "lucide-react";
import { ApiError, api } from "../api/client";

type Estado = { tipo: "idle" | "cargando" | "ok" | "error"; mensaje?: string };

function UploadCard({
  titulo,
  descripcion,
  onFile,
}: {
  titulo: string;
  descripcion: string;
  onFile: (f: File) => Promise<string>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [estado, setEstado] = useState<Estado>({ tipo: "idle" });

  const handleFile = async (file: File) => {
    setEstado({ tipo: "cargando" });
    try {
      const mensaje = await onFile(file);
      setEstado({ tipo: "ok", mensaje });
    } catch (e) {
      const mensaje = e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Error desconocido";
      setEstado({ tipo: "error", mensaje });
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <div className="panel-title">{titulo}</div>
      <p className="dim" style={{ fontSize: 12.5, marginTop: -6, marginBottom: 16, lineHeight: 1.5 }}>
        {descripcion}
      </p>
      <div className="upload-zone">
        <UploadCloud size={26} strokeWidth={1.5} />
        <div style={{ marginTop: 8 }}>Arrastra un archivo o selecciónalo abajo (.xls / .xlsx)</div>
        <input
          ref={inputRef}
          type="file"
          accept=".xls,.xlsx,.xlt,.xltx"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          disabled={estado.tipo === "cargando"}
        />
      </div>

      {estado.tipo === "cargando" && <p className="dim" style={{ fontSize: 12.5, marginTop: 10 }}>Procesando…</p>}
      {estado.tipo === "ok" && (
        <p style={{ fontSize: 12.5, marginTop: 10, color: "var(--ok)", display: "flex", alignItems: "center", gap: 6 }}>
          <CheckCircle2 size={14} /> {estado.mensaje}
        </p>
      )}
      {estado.tipo === "error" && (
        <p style={{ fontSize: 12.5, marginTop: 10, color: "var(--warn)", display: "flex", alignItems: "center", gap: 6 }}>
          <XCircle size={14} /> {estado.mensaje}
        </p>
      )}
    </div>
  );
}

export function Ingesta() {
  return (
    <>
      <div className="page-heading">
        <UploadCloud size={20} color="#c9974d" strokeWidth={1.8} />
        <h1>Ingesta de archivos</h1>
      </div>
      <p className="page-sub">
        Sube el reporte de producción de Sernapesca y/o el registro interno de trazabilidad. Los archivos ya
        procesados (mismo nombre + contenido) se rechazan automáticamente para evitar duplicados.
      </p>

      <UploadCard
        titulo="ReportePlantaProduccion (Sernapesca)"
        descripcion="Corre el motor de resolución Lote↔DI y actualiza el detalle acumulado, casos a revisar, y productividad diaria."
        onFile={async (f) => {
          const r = await api.subirProduccion(f);
          return `Procesado: ${r.lotes_ok} OK, ${r.lotes_ok_parcial} OK-parcial, ${r.lotes_revisar} a revisar, ${r.lotes_sin_determinar} sin determinar.`;
        }}
      />

      <UploadCard
        titulo="Trazabilidad interna (registro Lote-DI de la planta)"
        descripcion='Hoja "MATERIA PRIMA" con el lote interno (Guía MMPP) y su DI — se usa como tercera fuente en el cruce de 3 vías.'
        onFile={async (f) => {
          const r = await api.subirTrazabilidad(f);
          return `${r.filas_nuevas} filas nuevas agregadas al registro interno.`;
        }}
      />
    </>
  );
}
