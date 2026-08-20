import { Menu } from "lucide-react";
import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function handleKeyDown(event) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [menuOpen]);

  return (
    <div className={`app-shell${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <Sidebar
        open={menuOpen}
        collapsed={sidebarCollapsed}
        onClose={() => setMenuOpen(false)}
        onToggleCollapse={() => setSidebarCollapsed((current) => !current)}
      />
      <header className="mobile-header">
        <button
          className="icon-button"
          onClick={() => setMenuOpen(true)}
          aria-label="메뉴 열기"
          aria-expanded={menuOpen}
          aria-controls="app-sidebar"
        >
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
