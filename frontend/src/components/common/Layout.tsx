import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { History, LayoutDashboard, Menu, Plus, Upload } from "lucide-react";
import BackendStatus from "./BackendStatus";

function pageLabel(pathname: string): string {
  if (pathname === "/") return "Overview";
  if (pathname === "/history") return "Scan history";
  if (pathname === "/new") return "New scan";
  if (pathname.startsWith("/scans/")) return "Scan details";
  return "Not found";
}

export default function Layout() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => setMenuOpen(false), [pathname]);
  const historyActive = pathname === "/history" || pathname.startsWith("/scans/");
  return <div className="app"><div className="layout">
    <aside className={`sidebar${menuOpen ? " open" : ""}`}>
      <Link to="/" className="brand"><div className="brand-mark"><svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 2.8 20 6v5.8c0 4.7-3.4 7.7-8 9.5-4.6-1.8-8-4.8-8-9.5V6l8-3.2Z" /><path d="m8.3 12 2.4 2.4 5-5.2" /></svg></div><div><div className="brand-name">sentinel<span style={{ color: "var(--blue)" }}>.ai</span></div><div className="brand-sub">Code security platform</div></div></Link>
      <div><div className="nav-label">WORKSPACE</div><nav className="nav" aria-label="Main">
        <NavLink to="/" end className={({ isActive }) => isActive ? "active" : undefined}><LayoutDashboard aria-hidden="true" />Overview</NavLink>
        <NavLink to="/history" className={historyActive ? "active" : undefined}><History aria-hidden="true" />Scan history</NavLink>
        <NavLink to="/new" className={({ isActive }) => isActive ? "active" : undefined}><Upload aria-hidden="true" />New scan</NavLink>
      </nav></div>
      <div className="side-bottom"><BackendStatus /></div>
    </aside>
    <main><header className="topbar"><div style={{ display: "flex", alignItems: "center", gap: 12 }}><button type="button" className="icon-btn mobile-menu" aria-label="Toggle menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><Menu size={18} aria-hidden="true" /></button><div className="crumb">Workspace <span style={{ padding: "0 7px", color: "var(--line)" }}>/</span> <b>{pageLabel(pathname)}</b></div></div><div className="top-actions"><Link to="/new" className="btn btn-primary"><Plus aria-hidden="true" />New scan</Link></div></header>
      <div className="content">{pathname === "/" || pathname === "/new" ? <Outlet /> : <div className="legacy"><Outlet /></div>}</div></main>
  </div></div>;
}
