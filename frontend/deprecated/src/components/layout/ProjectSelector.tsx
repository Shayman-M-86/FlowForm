import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useApi } from "../../api/useApi";
import { useFetch } from "../../hooks/useFetch";
import {
  findProjectByRef,
  getStoredProjectSelection,
  projectSurveysPath,
  setStoredProjectSelection,
} from "./projectSelection";
import "./ProjectSelector.css";

export function ProjectSelector() {
  const { projectRef } = useParams<{ projectRef?: string }>();
  const { listProjects } = useApi();
  const navigate = useNavigate();
  const { data: projects, loading } = useFetch(() => listProjects(), [listProjects]);
  const currentProject = findProjectByRef(projects ?? [], projectRef);
  const [value, setValue] = useState("");

  useEffect(() => {
    if (currentProject) {
      setValue(currentProject.slug);
      setStoredProjectSelection(currentProject);
      return;
    }

    const stored = getStoredProjectSelection();
    if (stored) {
      setValue(stored.slug);
    }
  }, [currentProject]);

  function handleChange(nextSlug: string) {
    setValue(nextSlug);
    const project = (projects ?? []).find((entry) => entry.slug === nextSlug);
    if (!project) return;
    setStoredProjectSelection(project);
    navigate(projectSurveysPath(project));
  }

  return (
    <div className="project-selector">
      <label htmlFor="project-id" className="project-selector__label">
        Selected project
      </label>
      <select
        id="project-id"
        className="project-selector__input"
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        disabled={loading || !projects?.length}
      >
        <option value="">{loading ? "Loading projects..." : "Select a project"}</option>
        {(projects ?? []).map((project) => (
          <option key={project.id} value={project.slug}>
            {project.name} ({project.slug})
          </option>
        ))}
      </select>
    </div>
  );
}
