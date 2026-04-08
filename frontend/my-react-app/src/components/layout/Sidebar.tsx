import { NavLink, useParams } from "react-router-dom";
import { ProjectSelector } from "./ProjectSelector";
import "./Sidebar.css";

export function Sidebar() {
  const { projectId } = useParams<{ projectId?: string }>();

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo">FlowForm</span>
      </div>

      <nav className="sidebar__nav">
        {projectId && (
          <>
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
          </>
        )}
      </nav>

      <div className="sidebar__footer">
        <ProjectSelector />
      </div>
    </aside>
  );
}
