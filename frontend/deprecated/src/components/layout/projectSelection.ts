import type { ProjectOut } from "../../api/types";

const STORAGE_KEY = "flowform_selected_project";

export interface StoredProjectSelection {
  id: number;
  slug: string;
  name: string;
}

export function getStoredProjectSelection(): StoredProjectSelection | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<StoredProjectSelection>;
    if (
      typeof parsed.id !== "number" ||
      typeof parsed.slug !== "string" ||
      typeof parsed.name !== "string"
    ) {
      return null;
    }
    return parsed as StoredProjectSelection;
  } catch {
    return null;
  }
}

export function setStoredProjectSelection(project: ProjectOut): void {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ id: project.id, slug: project.slug, name: project.name }),
  );
}

export function getStoredProjectRef(): string | null {
  return getStoredProjectSelection()?.slug ?? null;
}

export function findProjectByRef(projects: ProjectOut[], ref?: string | null): ProjectOut | null {
  if (!projects.length) return null;
  if (ref) {
    const bySlug = projects.find((project) => project.slug === ref);
    if (bySlug) return bySlug;

    const byId = projects.find((project) => String(project.id) === ref);
    if (byId) return byId;
  }

  const stored = getStoredProjectSelection();
  if (stored) {
    const byStoredSlug = projects.find((project) => project.slug === stored.slug);
    if (byStoredSlug) return byStoredSlug;

    const byStoredId = projects.find((project) => project.id === stored.id);
    if (byStoredId) return byStoredId;
  }

  return projects[0] ?? null;
}

export function projectSurveysPath(project: Pick<ProjectOut, "slug">): string {
  return `/projects/${project.slug}/surveys`;
}

export function projectSurveyPath(
  project: Pick<ProjectOut, "slug">,
  surveyId: number,
): string {
  return `/projects/${project.slug}/surveys/${surveyId}`;
}

export function projectSubmissionsPath(project: Pick<ProjectOut, "slug">): string {
  return `/projects/${project.slug}/submissions`;
}

export function projectSurveySubmissionsPath(
  project: Pick<ProjectOut, "slug">,
  surveyId: number,
): string {
  return `/projects/${project.slug}/surveys/${surveyId}/submissions`;
}
