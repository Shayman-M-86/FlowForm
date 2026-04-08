import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./ProjectSelector.css";

const STORAGE_KEY = "flowform_project_id";

export function getStoredProjectId(): number | null {
  const v = localStorage.getItem(STORAGE_KEY);
  return v ? Number(v) : null;
}

export function ProjectSelector() {
  const { projectId } = useParams<{ projectId?: string }>();
  const navigate = useNavigate();
  const [value, setValue] = useState(projectId ?? String(getStoredProjectId() ?? ""));

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = parseInt(value, 10);
    if (isNaN(id) || id < 1) return;
    localStorage.setItem(STORAGE_KEY, String(id));
    navigate(`/projects/${id}/surveys`);
  }

  return (
    <form className="project-selector" onSubmit={handleSubmit}>
      <label htmlFor="project-id" className="project-selector__label">
        Project
      </label>
      <input
        id="project-id"
        type="number"
        min={1}
        className="project-selector__input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="ID"
      />
    </form>
  );
}
