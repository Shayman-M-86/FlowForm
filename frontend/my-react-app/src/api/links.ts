import { del, get, patch, post } from "./client";
import type {
  CreatePublicLinkOut,
  CreatePublicLinkRequest,
  ListPublicLinksOut,
  PublicLinkOut,
  UpdatePublicLinkRequest,
} from "./types";

const base = (p: number, s: number) =>
  `/api/v1/projects/${p}/surveys/${s}/public-links`;

export function listPublicLinks(
  projectId: number,
  surveyId: number,
): Promise<ListPublicLinksOut> {
  return get(base(projectId, surveyId));
}

export function createPublicLink(
  projectId: number,
  surveyId: number,
  data: CreatePublicLinkRequest,
): Promise<CreatePublicLinkOut> {
  return post(base(projectId, surveyId), data);
}

export function updatePublicLink(
  projectId: number,
  surveyId: number,
  linkId: number,
  data: UpdatePublicLinkRequest,
): Promise<PublicLinkOut> {
  return patch(`${base(projectId, surveyId)}/${linkId}`, data);
}

export function deletePublicLink(
  projectId: number,
  surveyId: number,
  linkId: number,
): Promise<void> {
  return del(`${base(projectId, surveyId)}/${linkId}`);
}
