import type {
  ApiExecutor,
  CreateQuestionRequest,
  CreateRuleRequest,
  CreateScoringRuleRequest,
  ProjectRef,
  QuestionOut,
  RuleOut,
  ScoringRuleOut,
  UpdateQuestionRequest,
  UpdateRuleRequest,
  UpdateScoringRuleRequest,
} from "./types";

const vBase = (p: ProjectRef, s: number, v: number) =>
  `/api/v1/projects/${p}/surveys/${s}/versions/${v}`;

// ── Questions ─────────────────────────────────────────────────────────────────

export function listQuestions(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
): Promise<QuestionOut[]> {
  return api.get<QuestionOut[]>(`${vBase(projectId, surveyId, versionNumber)}/questions`);
}

export function createQuestion(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  data: CreateQuestionRequest,
): Promise<QuestionOut> {
  return api.post<QuestionOut>(`${vBase(projectId, surveyId, versionNumber)}/questions`, data);
}

export function updateQuestion(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  questionId: number,
  data: UpdateQuestionRequest,
): Promise<QuestionOut> {
  return api.patch<QuestionOut>(
    `${vBase(projectId, surveyId, versionNumber)}/questions/${questionId}`,
    data,
  );
}

export function deleteQuestion(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  questionId: number,
): Promise<void> {
  return api.del(`${vBase(projectId, surveyId, versionNumber)}/questions/${questionId}`);
}

// ── Rules ─────────────────────────────────────────────────────────────────────

export function listRules(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
): Promise<RuleOut[]> {
  return api.get<RuleOut[]>(`${vBase(projectId, surveyId, versionNumber)}/rules`);
}

export function createRule(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  data: CreateRuleRequest,
): Promise<RuleOut> {
  return api.post<RuleOut>(`${vBase(projectId, surveyId, versionNumber)}/rules`, data);
}

export function updateRule(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  ruleId: number,
  data: UpdateRuleRequest,
): Promise<RuleOut> {
  return api.patch<RuleOut>(
    `${vBase(projectId, surveyId, versionNumber)}/rules/${ruleId}`,
    data,
  );
}

export function deleteRule(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  ruleId: number,
): Promise<void> {
  return api.del(`${vBase(projectId, surveyId, versionNumber)}/rules/${ruleId}`);
}

// ── Scoring Rules ─────────────────────────────────────────────────────────────

export function listScoringRules(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
): Promise<ScoringRuleOut[]> {
  return api.get<ScoringRuleOut[]>(`${vBase(projectId, surveyId, versionNumber)}/scoring-rules`);
}

export function createScoringRule(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  data: CreateScoringRuleRequest,
): Promise<ScoringRuleOut> {
  return api.post<ScoringRuleOut>(
    `${vBase(projectId, surveyId, versionNumber)}/scoring-rules`,
    data,
  );
}

export function updateScoringRule(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  scoringRuleId: number,
  data: UpdateScoringRuleRequest,
): Promise<ScoringRuleOut> {
  return api.patch<ScoringRuleOut>(
    `${vBase(projectId, surveyId, versionNumber)}/scoring-rules/${scoringRuleId}`,
    data,
  );
}

export function deleteScoringRule(
  api: ApiExecutor,
  projectId: ProjectRef,
  surveyId: number,
  versionNumber: number,
  scoringRuleId: number,
): Promise<void> {
  return api.del(`${vBase(projectId, surveyId, versionNumber)}/scoring-rules/${scoringRuleId}`);
}
