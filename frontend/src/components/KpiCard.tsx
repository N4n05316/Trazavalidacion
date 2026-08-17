import type { LucideIcon } from "lucide-react";

const TONE_COLOR: Record<string, string> = {
  ok: "#5ea37b",
  warn: "#c1594c",
  unk: "#b79a5c",
  brass: "#c9974d",
};

export function KpiCard({
  icon: Icon,
  label,
  value,
  tone,
  sub,
}: {
  icon: LucideIcon;
  label: string;
  value: number | string;
  tone: "ok" | "warn" | "unk" | "brass";
  sub?: string;
}) {
  const color = TONE_COLOR[tone];
  return (
    <div className="kpi-card" style={{ borderLeftColor: color }}>
      <div className="kpi-top">
        <Icon size={18} color={color} strokeWidth={1.75} />
        <span className="kpi-label">{label}</span>
      </div>
      <div className="kpi-value" style={{ color }}>
        {value}
      </div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}
