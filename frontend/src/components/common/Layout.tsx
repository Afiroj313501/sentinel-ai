import { Link, NavLink, Outlet } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import BackendStatus from "./BackendStatus";

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? "font-medium text-indigo-700" : "text-gray-600 hover:text-gray-900";
}

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2 text-lg font-semibold"><ShieldCheck className="h-6 w-6 text-indigo-600" aria-hidden="true" />Sentinel AI</Link>
          <nav className="flex items-center gap-4 text-sm">
            <NavLink to="/" end className={navClass}>Scans</NavLink>
            <NavLink to="/new" className={navClass}>New scan</NavLink>
            <BackendStatus />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8"><Outlet /></main>
    </div>
  );
}
