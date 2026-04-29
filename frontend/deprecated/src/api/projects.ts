import type { ApiExecutor, CreateProjectRequest, ProjectOut } from "./types";

export function listProjects(api: ApiExecutor): Promise<ProjectOut[]> {
  return api.get<ProjectOut[]>("/api/v1/projects");
}

export function createProject(
  api: ApiExecutor,
  data: CreateProjectRequest,
): Promise<ProjectOut> {
  return api.post<ProjectOut>("/api/v1/projects", data);
}
