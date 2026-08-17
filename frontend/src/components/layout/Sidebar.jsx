import {
  BookOpen,
  ChevronDown,
  ChevronLeft,
  Clock3,
  Languages,
  Settings,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAppData } from "../../context/appData";
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

function MenuLink({ item, onClick }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onClick}
      className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
    >
      <Icon size={20} strokeWidth={1.8} />
      <span>{item.label}</span>
    </NavLink>
  );
}

export default function Sidebar({ open, onClose }) {
  const { team } = useAppData();

  return (
    <>
      <button
        className={`sidebar-scrim${open ? " visible" : ""}`}
        onClick={onClose}
        aria-label="메뉴 닫기"
      />
      <aside className={`sidebar${open ? " open" : ""}`}>
        <div className="sidebar-top">
          <div className="sidebar-brand-row">
            <NavLink className="brand" to="/translate" onClick={onClose}>Glossy.</NavLink>
            <button className="sidebar-collapse" onClick={onClose} aria-label="사이드바 닫기">
              <ChevronLeft size={23} />
            </button>
            <button className="sidebar-mobile-close" onClick={onClose} aria-label="메뉴 닫기">
              <X size={22} />
            </button>
          </div>

          <button className="team-selector" title="현재 팀">
            <span>{team.name}</span>
            <ChevronDown size={18} />
          </button>

          <nav className="sidebar-menu" aria-label="주요 메뉴">
            {mainItems.map((item) => <MenuLink key={item.to} item={item} onClick={onClose} />)}
          </nav>
        </div>

        <nav className="sidebar-bottom" aria-label="설정 메뉴">
          {bottomItems.map((item) => <MenuLink key={item.to} item={item} onClick={onClose} />)}
        </nav>
      </aside>
    </>
  );
}
