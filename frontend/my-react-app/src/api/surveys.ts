import { del, get, patch, post } from "./client";
import type {
  CreateSurveyRequest,
  SurveyOut,
  SurveyVersionOut,
  UpdateSurveyRequest,
} from "./types";

// ── Surveys ───────────────────────────────────────────────────────────────────

export function listSurveys(
  projectId: number,
  headers?: HeadersInit,
): Promise<SurveyOut[]> {
  return get(`/api/v1/projects/${projectId}/surveys`, headers);
}

export function getSurvey(
  projectId: number,
  surveyId: number,
  headers?: HeadersInit,
): Promise<SurveyOut> {
  return get(`/api/v1/projects/${projectId}/surveys/${surveyId}`, headers);
}

export function createSurvey(
  projectId: number,
  data: CreateSurveyRequest,
  headers?: HeadersInit,
): Promise<SurveyOut> {
  return post(`/api/v1/projects/${projectId}/surveys`, data, headers);
}

export function updateSurvey(
  projectId: number,
  surveyId: number,
  data: UpdateSurveyRequest,
  headers?: HeadersInit,
): Promise<SurveyOut> {
  return patch(
    `/api/v1/projects/${projectId}/surveys/${surveyId}`,
    data,
    headers,
  );
}

export function deleteSurvey(
  projectId: number,
  surveyId: number,
  headers?: HeadersInit,
): Promise<void> {
  return del(`/api/v1/projects/${projectId}/surveys/${surveyId}`, headers);
}

// ── Versions ──────────────────────────────────────────────────────────────────

export function listVersions(
  projectId: number,
  surveyId: number,
  headers?: HeadersInit,
): Promise<SurveyVersionOut[]> {
  return get(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions`,
    headers,
  );
}

export function getVersion(
  projectId: number,
  surveyId: number,
  versionId: number,
  headers?: HeadersInit,
): Promise<SurveyVersionOut> {
  return get(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions/${versionId}`,
    headers,
  );
}

export function createVersion(
  projectId: number,
  surveyId: number,
  headers?: HeadersInit,
): Promise<SurveyVersionOut> {
  return post(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions`,
    undefined,
    headers,
  );
}

export function publishVersion(
  projectId: number,
  surveyId: number,
  versionId: number,
  headers?: HeadersInit,
): Promise<SurveyVersionOut> {
  return post(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions/${versionId}/publish`,
    undefined,
    headers,
  );
}

export function archiveVersion(
  projectId: number,
  surveyId: number,
  versionId: number,
  headers?: HeadersInit,
): Promise<SurveyVersionOut> {
  return post(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions/${versionId}/archive`,
    undefined,
    headers,
  );
}