const COLORS = { ok: "#5ea37b", warn: "#c1594c" };

export function Seal({ status = "revisar", size = 64 }: { status?: "ok" | "revisar"; size?: number }) {
  const label = status === "ok" ? "VERIFICADO" : "REVISAR";
  const color = status === "ok" ? COLORS.ok : COLORS.warn;
  return (
    <div className="seal" style={{ width: size, height: size, borderColor: color, color }}>
      <svg viewBox="0 0 100 100" width={size} height={size} className="seal-ring">
        <circle cx="50" cy="50" r="46" fill="none" stroke={color} strokeWidth="1.4" strokeDasharray="2 3" />
      </svg>
      <div className="seal-inner" style={{ borderColor: color }}>
        <span>{label}</span>
      </div>
    </div>
  );
}
