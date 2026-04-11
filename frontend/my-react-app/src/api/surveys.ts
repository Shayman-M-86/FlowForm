import type {
  ApiExecutor,
  CreateSurveyRequest,
  SurveyOut,
  SurveyVersionOut,
  UpdateSurveyRequest,
} from "./types";

// ── Surveys ───────────────────────────────────────────────────────────────────

export function listSurveys(api: ApiExecutor, projectId: number): Promise<SurveyOut[]> {
  return api.get<SurveyOut[]>(`/api/v1/projects/${projectId}/surveys`);
}

export function getSurvey(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
): Promise<SurveyOut> {
  return api.get<SurveyOut>(`/api/v1/projects/${projectId}/surveys/${surveyId}`);
}

export function createSurvey(
  api: ApiExecutor,
  projectId: number,
  data: CreateSurveyRequest,
): Promise<SurveyOut> {
  return api.post<SurveyOut>(`/api/v1/projects/${projectId}/surveys`, data);
}

export function updateSurvey(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  data: UpdateSurveyRequest,
): Promise<SurveyOut> {
  return api.patch<SurveyOut>(`/api/v1/projects/${projectId}/surveys/${surveyId}`, data);
}

export function deleteSurvey(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
): Promise<void> {
  return api.del(`/api/v1/projects/${projectId}/surveys/${surveyId}`);
}

// ── Versions ──────────────────────────────────────────────────────────────────

export function listVersions(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
): Promise<SurveyVersionOut[]> {
  return api.get<SurveyVersionOut[]>(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions`,
  );
}

export function getVersion(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionNumber: number,
): Promise<SurveyVersionOut> {
  return api.get<SurveyVersionOut>(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions/${versionNumber}`,
  );
}

export function createVersion(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
): Promise<SurveyVersionOut> {
  return api.post<SurveyVersionOut>(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions`,
  );
}

export function publishVersion(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionNumber: number,
): Promise<SurveyVersionOut> {
  return api.post<SurveyVersionOut>(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions/${versionNumber}/publish`,
  );
}

export function archiveVersion(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionNumber: number,
): Promise<SurveyVersionOut> {
  return api.post<SurveyVersionOut>(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/versions/${versionNumber}/archive`,
  );
}
