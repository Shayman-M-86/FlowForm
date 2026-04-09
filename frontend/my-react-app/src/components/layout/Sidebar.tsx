import { NavLink, useParams } from "react-router-dom";
import { ProjectSelector } from "./ProjectSelector";
import { AuthButtons } from "./AuthButtons";
import { getStoredProjectId } from "./ProjectSelector";
import "./Sidebar.css";

export function Sidebar() {
  const { projectId: paramProjectId } = useParams<{ projectId?: string }>();
  const projectId = paramProjectId ?? String(getStoredProjectId() ?? 1);

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo">
          FlowForm
          <span className="sidebar__logo-mark">Survey Builder</span>
        </span>
      </div>

      <nav className="sidebar__nav">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
          }
          end
        >
          Home
        </NavLink>

        <div className="sidebar__section-label">Build</div>

        <NavLink
          to={`/projects/${projectId}/surveys`}
          className={({ isActive }) =>
            `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
          }
          end
        >
          Surveys
        </NavLink>
        <NavLink
          to={`/projects/${projectId}/submissions`}
          className={({ isActive }) =>
            `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
          }
        >
          Submissions
        </NavLink>

        <div className="sidebar__section-label">Take</div>

        <NavLink
          to="/take"
          className={({ isActive }) =>
            `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
          }
        >
          Fill out a survey
        </NavLink>
      </nav>

      <div className="sidebar__footer">
        <ProjectSelector />
        <AuthButtons />
      </div>
    </aside>
  );
}
