import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function CenterMessage({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: ReactNode }) {
  return (
    <div className="center-msg">
      <Icon size={28} strokeWidth={1.5} color="#c9974d" />
      <div className="center-msg-title">{title}</div>
      {children && <div className="center-msg-body">{children}</div>}
    </div>
  );
}
