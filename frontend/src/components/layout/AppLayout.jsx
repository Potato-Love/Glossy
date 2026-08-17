import { Menu } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <header className="mobile-header">
        <button className="icon-button" onClick={() => setMenuOpen(true)} aria-label="메뉴 열기">
          <Menu size={22} />
        </button>
        <span className="mobile-logo">Glossy.</span>
      </header>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
