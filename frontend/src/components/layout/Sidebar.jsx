import {
  BookOpen,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Languages,
  LogOut,
  Plus,
  Settings,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAppData } from "../../context/appData";
import { useAuth } from "../../context/authContext";
import "./Sidebar.css";

const mainItems = [
  { to: "/translate", label: "번역", icon: Languages },
  { to: "/glossary", label: "용어집", icon: BookOpen },
  { to: "/recipients", label: "상대 프로필", icon: UserRound },
  { to: "/history", label: "히스토리", icon: Clock3 },
];

const bottomItems = [
  { to: "/my", label: "내 정보", icon: Settings },
  { to: "/team", label: "팀", icon: UsersRound },
];

function MenuLink({ item, onClick, collapsed }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onClick}
      className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
      aria-label={collapsed ? item.label : undefined}
      title={collapsed ? item.label : undefined}
    >
      <Icon size={20} strokeWidth={1.8} />
      <span>{item.label}</span>
    </NavLink>
  );
}

export default function Sidebar({ open, collapsed, onClose, onToggleCollapse }) {
  const { team } = useAppData();
  const auth = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await auth.logout();
    onClose();
    navigate("/login", { replace: true });
  }

  return (
    <>
      <button
        className={`sidebar-scrim${open ? " visible" : ""}`}
        onClick={onClose}
        aria-label="메뉴 닫기"
      />
      <aside id="app-sidebar" className={`sidebar${open ? " open" : ""}${collapsed ? " collapsed" : ""}`}>
        <div className="sidebar-top">
          <div className="sidebar-brand-row">
            <NavLink className="brand" to="/translate" onClick={onClose}>Glossy.</NavLink>
            <button
              className="sidebar-collapse"
              onClick={onToggleCollapse}
              aria-label={collapsed ? "사이드바 펼치기" : "사이드바 축소하기"}
              title={collapsed ? "사이드바 펼치기" : "사이드바 축소하기"}
              aria-expanded={!collapsed}
            >
              {collapsed ? <ChevronRight size={23} /> : <ChevronLeft size={23} />}
            </button>
            <button className="sidebar-mobile-close" onClick={onClose} aria-label="메뉴 닫기">
              <X size={22} />
            </button>
          </div>

          <div className="team-selector-wrap">
            <label htmlFor="sidebarTeam">현재 팀</label>
            <div className="team-selector-control">
              <UsersRound size={16} strokeWidth={1.8} aria-hidden="true" />
              <select id="sidebarTeam" className="team-selector" value={team.id} onChange={(event) => auth.switchTeam(event.target.value)}>
                {auth.teams.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}
              </select>
              <ChevronDown className="team-selector-chevron" size={16} aria-hidden="true" />
            </div>
            <NavLink className="team-add-link" to="/onboarding" onClick={onClose}><Plus size={15} /> 팀 만들기·가입</NavLink>
          </div>

          <nav className="sidebar-menu" aria-label="주요 메뉴">
            {mainItems.map((item) => <MenuLink key={item.to} item={item} onClick={onClose} collapsed={collapsed} />)}
          </nav>
        </div>

        <nav className="sidebar-bottom" aria-label="설정 메뉴">
          {bottomItems.map((item) => <MenuLink key={item.to} item={item} onClick={onClose} collapsed={collapsed} />)}
          <button className="sidebar-link sidebar-logout" onClick={handleLogout} aria-label={collapsed ? "로그아웃" : undefined} title={collapsed ? "로그아웃" : undefined}><LogOut size={20} strokeWidth={1.8} /><span>로그아웃</span></button>
        </nav>
      </aside>
    </>
  );
}
