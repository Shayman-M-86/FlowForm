import type {
  ApiExecutor,
  CreatePublicLinkOut,
  CreatePublicLinkRequest,
  ListPublicLinksOut,
  PublicLinkOut,
  UpdatePublicLinkRequest,
} from "./types";

const base = (p: number, s: number) =>
  `/api/v1/projects/${p}/surveys/${s}/public-links`;

export function listPublicLinks(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
): Promise<ListPublicLinksOut> {
  return api.get<ListPublicLinksOut>(base(projectId, surveyId));
}

export function createPublicLink(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  data: CreatePublicLinkRequest,
): Promise<CreatePublicLinkOut> {
  return api.post<CreatePublicLinkOut>(base(projectId, surveyId), data);
}

export function updatePublicLink(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  linkId: number,
  data: UpdatePublicLinkRequest,
): Promise<PublicLinkOut> {
  return api.patch<PublicLinkOut>(`${base(projectId, surveyId)}/${linkId}`, data);
}

export function deletePublicLink(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  linkId: number,
): Promise<void> {
  return api.del(`${base(projectId, surveyId)}/${linkId}`);
}
