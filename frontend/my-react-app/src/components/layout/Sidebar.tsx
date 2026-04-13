import { NavLink, useParams } from "react-router-dom";
import { ProjectSelector } from "./ProjectSelector";
import { AuthButtons } from "./AuthButtons";
import { ModeToggle } from "./ModeToggle";
import type { AppMode } from "../../hooks/useAppMode";
import { useProjectContext } from "../../hooks/useProjectContext";
import { getStoredProjectRef, projectSubmissionsPath, projectSurveysPath } from "./projectSelection";
import "./Sidebar.css";

interface SidebarProps {
  mode: AppMode;
  onModeSwitch: (m: AppMode) => void;
}

export function Sidebar({ mode, onModeSwitch }: SidebarProps) {
  const { projectRef: paramProjectRef } = useParams<{ projectRef?: string }>();
  const fallbackProjectRef = paramProjectRef ?? getStoredProjectRef();
  const { currentProject } = useProjectContext(fallbackProjectRef);
  const surveysPath = currentProject ? projectSurveysPath(currentProject) : "/projects";
  const submissionsPath = currentProject ? projectSubmissionsPath(currentProject) : "/projects";

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

        <NavLink
          to="/projects"
          className={({ isActive }) =>
            `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
          }
          end
        >
          Projects
        </NavLink>

        <div className="sidebar__section-label">Build</div>

        {currentProject && (
          <div className="sidebar__project-chip">
            <span className="sidebar__project-chip-label">Current</span>
            <strong>{currentProject.name}</strong>
            <span className="sidebar__project-chip-slug">/{currentProject.slug}</span>
          </div>
        )}

        <NavLink
          to={surveysPath}
          className={({ isActive }) =>
            `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
          }
          end
        >
          Surveys
        </NavLink>
        <NavLink
          to={submissionsPath}
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
        <ModeToggle mode={mode} onSwitch={onModeSwitch} />
        <ProjectSelector />
        <AuthButtons />
      </div>
    </aside>
  );
}
