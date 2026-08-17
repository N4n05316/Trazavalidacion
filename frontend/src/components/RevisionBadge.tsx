import type { EstadoRevision } from "../api/types";

const MAP: Record<EstadoRevision, { bg: string; color: string; label: string }> = {
  PENDIENTE: { bg: "rgba(183,154,92,0.18)", color: "#b79a5c", label: "Pendiente" },
  "CONFIRMADO ERROR": { bg: "rgba(193,89,76,0.2)", color: "#c1594c", label: "Confirmado error" },
  "FALSO POSITIVO": { bg: "rgba(94,163,123,0.18)", color: "#5ea37b", label: "Falso positivo" },
};

export function RevisionBadge({ status }: { status: EstadoRevision }) {
  const s = MAP[status] ?? MAP.PENDIENTE;
  return (
    <span className="rev-badge" style={{ background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
}
