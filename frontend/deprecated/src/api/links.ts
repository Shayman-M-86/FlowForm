import type {
  ApiExecutor,
  CreatePublicLinkOut,
  CreatePublicLinkRequest,
  ListPublicLinksOut,
  ProjectRef,
  PublicLinkOut,
  UpdatePublicLinkRequest,
} from "./types";

const base = (p: ProjectRef, s: number) =>
  `/api/v1/projects/${p}/surveys/${s}/links`;

export function listPublicLinks(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
): Promise<ListPublicLinksOut> {
  return api.get<ListPublicLinksOut>(base(projectId, surveyId));
}

export function createPublicLink(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  data: CreatePublicLinkRequest,
): Promise<CreatePublicLinkOut> {
  return api.post<CreatePublicLinkOut>(base(projectId, surveyId), data);
}

export function updatePublicLink(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  linkId: number,
  data: UpdatePublicLinkRequest,
): Promise<PublicLinkOut> {
  return api.patch<PublicLinkOut>(`${base(projectId, surveyId)}/${linkId}`, data);
}

export function deletePublicLink(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  linkId: number,
): Promise<void> {
  return api.del(`${base(projectId, surveyId)}/${linkId}`);
}
