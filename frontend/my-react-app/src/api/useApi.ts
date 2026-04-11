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
  CreateSubmissionRequest,
  CreateSurveyRequest,
  ListSubmissionsParams,
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
      listSurveys: (projectId: number) =>
        surveysApi.listSurveys(executor, projectId),
      getSurvey: (projectId: number, surveyId: number) =>
        surveysApi.getSurvey(executor, projectId, surveyId),
      createSurvey: (projectId: number, data: CreateSurveyRequest) =>
        surveysApi.createSurvey(executor, projectId, data),
      updateSurvey: (projectId: number, surveyId: number, data: UpdateSurveyRequest) =>
        surveysApi.updateSurvey(executor, projectId, surveyId, data),
      deleteSurvey: (projectId: number, surveyId: number) =>
        surveysApi.deleteSurvey(executor, projectId, surveyId),

      // ── Versions ─────────────────────────────────────────────────────────────
      listVersions: (projectId: number, surveyId: number) =>
        surveysApi.listVersions(executor, projectId, surveyId),
      getVersion: (projectId: number, surveyId: number, versionNumber: number) =>
        surveysApi.getVersion(executor, projectId, surveyId, versionNumber),
      createVersion: (projectId: number, surveyId: number) =>
        surveysApi.createVersion(executor, projectId, surveyId),
      publishVersion: (projectId: number, surveyId: number, versionNumber: number) =>
        surveysApi.publishVersion(executor, projectId, surveyId, versionNumber),
      archiveVersion: (projectId: number, surveyId: number, versionNumber: number) =>
        surveysApi.archiveVersion(executor, projectId, surveyId, versionNumber),

      // ── Questions ────────────────────────────────────────────────────────────
      listQuestions: (projectId: number, surveyId: number, versionNumber: number) =>
        contentApi.listQuestions(executor, projectId, surveyId, versionNumber),
      createQuestion: (
        projectId: number,
        surveyId: number,
        versionNumber: number,
        data: CreateQuestionRequest,
      ) => contentApi.createQuestion(executor, projectId, surveyId, versionNumber, data),
      updateQuestion: (
        projectId: number,
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
        projectId: number,
        surveyId: number,
        versionNumber: number,
        questionId: number,
      ) => contentApi.deleteQuestion(executor, projectId, surveyId, versionNumber, questionId),

      // ── Rules ────────────────────────────────────────────────────────────────
      listRules: (projectId: number, surveyId: number, versionNumber: number) =>
        contentApi.listRules(executor, projectId, surveyId, versionNumber),
      createRule: (
        projectId: number,
        surveyId: number,
        versionNumber: number,
        data: CreateRuleRequest,
      ) => contentApi.createRule(executor, projectId, surveyId, versionNumber, data),
      updateRule: (
        projectId: number,
        surveyId: number,
        versionNumber: number,
        ruleId: number,
        data: UpdateRuleRequest,
      ) => contentApi.updateRule(executor, projectId, surveyId, versionNumber, ruleId, data),
      deleteRule: (
        projectId: number,
        surveyId: number,
        versionNumber: number,
        ruleId: number,
      ) => contentApi.deleteRule(executor, projectId, surveyId, versionNumber, ruleId),

      // ── Scoring Rules ────────────────────────────────────────────────────────
      listScoringRules: (projectId: number, surveyId: number, versionNumber: number) =>
        contentApi.listScoringRules(executor, projectId, surveyId, versionNumber),
      createScoringRule: (
        projectId: number,
        surveyId: number,
        versionNumber: number,
        data: CreateScoringRuleRequest,
      ) => contentApi.createScoringRule(executor, projectId, surveyId, versionNumber, data),
      updateScoringRule: (
        projectId: number,
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
        projectId: number,
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
      listPublicLinks: (projectId: number, surveyId: number) =>
        linksApi.listPublicLinks(executor, projectId, surveyId),
      createPublicLink: (
        projectId: number,
        surveyId: number,
        data: CreatePublicLinkRequest,
      ) => linksApi.createPublicLink(executor, projectId, surveyId, data),
      updatePublicLink: (
        projectId: number,
        surveyId: number,
        linkId: number,
        data: UpdatePublicLinkRequest,
      ) => linksApi.updatePublicLink(executor, projectId, surveyId, linkId, data),
      deletePublicLink: (projectId: number, surveyId: number, linkId: number) =>
        linksApi.deletePublicLink(executor, projectId, surveyId, linkId),

      // ── Submissions ──────────────────────────────────────────────────────────
      listSubmissions: (projectId: number, params?: ListSubmissionsParams) =>
        submissionsApi.listSubmissions(executor, projectId, params),
      getSubmission: (projectId: number, submissionId: number, includeAnswers?: boolean) =>
        submissionsApi.getSubmission(executor, projectId, submissionId, includeAnswers),
      createSubmission: (
        projectId: number,
        surveyId: number,
        data: CreateSubmissionRequest,
      ) => submissionsApi.createSubmission(executor, projectId, surveyId, data),
    }),
    [executor],
  );
}
