import { useCallback, useMemo } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import * as authApi from "./auth";
import * as client from "./client";
import * as projectsApi from "./projects";
import * as surveysApi from "./surveys";
import * as contentApi from "./content";
import * as linksApi from "./links";
import * as submissionsApi from "./submissions";
import type {
  ApiExecutor,
  CreateProjectRequest,
  CreatePublicLinkRequest,
  CreateQuestionRequest,
  CreateRuleRequest,
  CreateScoringRuleRequest,
  CreateSurveyRequest,
  ListSubmissionsParams,
  ProjectRef,
  UpdatePublicLinkRequest,
  UpdateQuestionRequest,
  UpdateRuleRequest,
  UpdateScoringRuleRequest,
  UpdateSurveyRequest,
} from "./types";

export function useApi() {
  const { getAccessTokenSilently } = useAuth0();

  const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
    const token = await getAccessTokenSilently({
      authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE },
    });
    return { Authorization: `Bearer ${token}` };
  }, [getAccessTokenSilently]);

  const executor = useMemo(
    (): ApiExecutor => ({
      get: <T,>(path: string) => getAuthHeaders().then((h) => client.get<T>(path, h)),
      post: <T,>(path: string, body?: unknown) =>
        getAuthHeaders().then((h) => client.post<T>(path, body, h)),
      patch: <T,>(path: string, body: unknown) =>
        getAuthHeaders().then((h) => client.patch<T>(path, body, h)),
      del: (path: string) => getAuthHeaders().then((h) => client.del(path, h)),
      getWithQuery: <T,>(
        path: string,
        params: Record<string, string | number | boolean | undefined>,
      ) => getAuthHeaders().then((h) => client.getWithQuery<T>(path, params, h)),
    }),
    [getAuthHeaders],
  );

  return useMemo(
    () => ({
      // ── Auth ─────────────────────────────────────────────────────────────────
      bootstrapCurrentUser: (idToken: string) =>
        authApi.bootstrapCurrentUser(executor, idToken),

      // ── Projects ─────────────────────────────────────────────────────────────
      listProjects: () =>
        projectsApi.listProjects(executor),
      createProject: (data: CreateProjectRequest) =>
        projectsApi.createProject(executor, data),

      // ── Surveys ──────────────────────────────────────────────────────────────
      listSurveys: (projectId: ProjectRef) =>
        surveysApi.listSurveys(executor, projectId),
      getSurvey: (projectId: ProjectRef, surveyId: number) =>
        surveysApi.getSurvey(executor, projectId, surveyId),
      createSurvey: (projectId: ProjectRef, data: CreateSurveyRequest) =>
        surveysApi.createSurvey(executor, projectId, data),
      updateSurvey: (projectId: ProjectRef, surveyId: number, data: UpdateSurveyRequest) =>
        surveysApi.updateSurvey(executor, projectId, surveyId, data),
      deleteSurvey: (projectId: ProjectRef, surveyId: number) =>
        surveysApi.deleteSurvey(executor, projectId, surveyId),

      // ── Versions ─────────────────────────────────────────────────────────────
      listVersions: (projectId: ProjectRef, surveyId: number) =>
        surveysApi.listVersions(executor, projectId, surveyId),
      getVersion: (projectId: ProjectRef, surveyId: number, versionNumber: number) =>
        surveysApi.getVersion(executor, projectId, surveyId, versionNumber),
      createVersion: (projectId: ProjectRef, surveyId: number) =>
        surveysApi.createVersion(executor, projectId, surveyId),
      copyVersionToDraft: (projectId: ProjectRef, surveyId: number, versionNumber: number) =>
        surveysApi.copyVersionToDraft(executor, projectId, surveyId, versionNumber),
      publishVersion: (projectId: ProjectRef, surveyId: number, versionNumber: number) =>
        surveysApi.publishVersion(executor, projectId, surveyId, versionNumber),
      archiveVersion: (projectId: ProjectRef, surveyId: number, versionNumber: number) =>
        surveysApi.archiveVersion(executor, projectId, surveyId, versionNumber),

      // ── Questions ────────────────────────────────────────────────────────────
      listQuestions: (projectId: ProjectRef, surveyId: number, versionNumber: number) =>
        contentApi.listQuestions(executor, projectId, surveyId, versionNumber),
      createQuestion: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        data: CreateQuestionRequest,
      ) => contentApi.createQuestion(executor, projectId, surveyId, versionNumber, data),
      updateQuestion: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        questionId: number,
        data: UpdateQuestionRequest,
      ) =>
        contentApi.updateQuestion(
          executor,
          projectId,
          surveyId,
          versionNumber,
          questionId,
          data,
        ),
      deleteQuestion: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        questionId: number,
      ) => contentApi.deleteQuestion(executor, projectId, surveyId, versionNumber, questionId),

      // ── Rules ────────────────────────────────────────────────────────────────
      listRules: (projectId: ProjectRef, surveyId: number, versionNumber: number) =>
        contentApi.listRules(executor, projectId, surveyId, versionNumber),
      createRule: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        data: CreateRuleRequest,
      ) => contentApi.createRule(executor, projectId, surveyId, versionNumber, data),
      updateRule: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        ruleId: number,
        data: UpdateRuleRequest,
      ) => contentApi.updateRule(executor, projectId, surveyId, versionNumber, ruleId, data),
      deleteRule: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        ruleId: number,
      ) => contentApi.deleteRule(executor, projectId, surveyId, versionNumber, ruleId),

      // ── Scoring Rules ────────────────────────────────────────────────────────
      listScoringRules: (projectId: ProjectRef, surveyId: number, versionNumber: number) =>
        contentApi.listScoringRules(executor, projectId, surveyId, versionNumber),
      createScoringRule: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        data: CreateScoringRuleRequest,
      ) => contentApi.createScoringRule(executor, projectId, surveyId, versionNumber, data),
      updateScoringRule: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        scoringRuleId: number,
        data: UpdateScoringRuleRequest,
      ) =>
        contentApi.updateScoringRule(
          executor,
          projectId,
          surveyId,
          versionNumber,
          scoringRuleId,
          data,
        ),
      deleteScoringRule: (
        projectId: ProjectRef,
        surveyId: number,
        versionNumber: number,
        scoringRuleId: number,
      ) =>
        contentApi.deleteScoringRule(
          executor,
          projectId,
          surveyId,
          versionNumber,
          scoringRuleId,
        ),

      // ── Public Links ─────────────────────────────────────────────────────────
      listPublicLinks: (projectId: ProjectRef, surveyId: number) =>
        linksApi.listPublicLinks(executor, projectId, surveyId),
      createPublicLink: (
        projectId: ProjectRef,
        surveyId: number,
        data: CreatePublicLinkRequest,
      ) => linksApi.createPublicLink(executor, projectId, surveyId, data),
      updatePublicLink: (
        projectId: ProjectRef,
        surveyId: number,
        linkId: number,
        data: UpdatePublicLinkRequest,
      ) => linksApi.updatePublicLink(executor, projectId, surveyId, linkId, data),
      deletePublicLink: (projectId: ProjectRef, surveyId: number, linkId: number) =>
        linksApi.deletePublicLink(executor, projectId, surveyId, linkId),

      // ── Submissions ──────────────────────────────────────────────────────────
      listSubmissions: (projectId: ProjectRef, params?: ListSubmissionsParams) =>
        submissionsApi.listSubmissions(executor, projectId, params),
      getSubmission: (projectId: ProjectRef, submissionId: number, includeAnswers?: boolean) =>
        submissionsApi.getSubmission(executor, projectId, submissionId, includeAnswers),
    }),
    [executor],
  );
}
