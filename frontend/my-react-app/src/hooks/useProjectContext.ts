import { useEffect, useMemo } from "react";
import type { ProjectOut } from "../api/types";
import { useApi } from "../api/useApi";
import {
  findProjectByRef,
  setStoredProjectSelection,
} from "../components/layout/projectSelection";
import { useFetch } from "./useFetch";

export interface ProjectContextResult {
  projects: ProjectOut[];
  currentProject: ProjectOut | null;
  projectId: number | null;
  projectRef: string | null;
  loading: boolean;
  error: string | null;
}

export function useProjectContext(projectRef?: string | null): ProjectContextResult {
  const { listProjects } = useApi();
  const { data, loading, error } = useFetch(() => listProjects(), [listProjects]);

  const projects = data ?? [];
  const currentProject = useMemo(
    () => findProjectByRef(projects, projectRef),
    [projectRef, projects],
  );

  useEffect(() => {
    if (currentProject) {
      setStoredProjectSelection(currentProject);
    }
  }, [currentProject]);

  return {
    projects,
    currentProject,
    projectId: currentProject?.id ?? null,
    projectRef: currentProject?.slug ?? null,
    loading,
    error,
  };
}
