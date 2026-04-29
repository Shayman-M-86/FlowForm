import { NavLink } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { ModeToggle } from "./ModeToggle";
import type { AppMode } from "../../hooks/useAppMode";
import "./PublicShell.css";

interface PublicShellProps {
  mode: AppMode;
  onModeSwitch: (m: AppMode) => void;
}

export function PublicShell({ mode, onModeSwitch }: PublicShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__logo">
            FlowForm
            <span className="sidebar__logo-mark">Survey Platform</span>
          </span>
        </div>

        <nav className="sidebar__nav">
          <div className="sidebar__section-label">Explore</div>

          <NavLink
            to="/explore"
            end
            className={({ isActive }) =>
              `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
            }
          >
            Browse surveys
          </NavLink>

          <NavLink
            to="/explore/take"
            className={({ isActive }) =>
              `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
            }
          >
            Take a survey
          </NavLink>
        </nav>

        <div className="sidebar__footer">
          <ModeToggle mode={mode} onSwitch={onModeSwitch} />
        </div>
      </aside>

      <main className="app-shell__main">
        <Outlet />
      </main>
    </div>
  );
}
