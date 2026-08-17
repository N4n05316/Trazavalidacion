import { Anchor, Download, LogOut, Waves } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { exportarExcelUrl } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const NAV_ITEMS: { to: string; label: string; end?: boolean }[] = [
  { to: "/", label: "Resumen", end: true },
  { to: "/casos", label: "Casos a revisar" },
  { to: "/balance-masa", label: "Balance de masa" },
  { to: "/declaraciones", label: "Declaraciones" },
  { to: "/cruce", label: "Cruce 3 vías" },
  { to: "/ingesta", label: "Ingesta" },
];

export function Layout() {
  const { usuario, cerrarSesion } = useAuth();
  const navItems = usuario?.rol === "admin" ? [...NAV_ITEMS, { to: "/usuarios", label: "Usuarios" }] : NAV_ITEMS;

  return (
    <div>
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Waves size={20} strokeWidth={1.6} />
          </div>
          <div>
            <div className="brand-name">Certus</div>
            <div className="brand-tag">Trazabilidad Lote &harr; DI, verificada</div>
          </div>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div className="plant-pill">
            <Anchor size={13} strokeWidth={1.8} />
            Pesquera Friosur SpA — Reg. 11004
          </div>
          <a
            href={exportarExcelUrl()}
            className="btn btn-ghost"
            style={{ padding: "5px 10px", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}
            title="Descargar Excel de auditoría"
          >
            <Download size={13} />
            Excel
          </a>
          {usuario && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11.5 }} className="dim">
              <span className="mono" title={usuario.email}>
                {usuario.nombre}
              </span>
              <button className="btn btn-ghost" style={{ padding: "5px 9px" }} onClick={cerrarSesion} title="Cerrar sesión">
                <LogOut size={13} />
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="content">
        <Outlet />
      </main>

      <footer className="footer">Certus — Pesquera Friosur SpA</footer>
    </div>
  );
}
