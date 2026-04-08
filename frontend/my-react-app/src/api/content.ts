import type {
  ApiExecutor,
  CreateQuestionRequest,
  CreateRuleRequest,
  CreateScoringRuleRequest,
  QuestionOut,
  RuleOut,
  ScoringRuleOut,
  UpdateQuestionRequest,
  UpdateRuleRequest,
  UpdateScoringRuleRequest,
} from "./types";

const vBase = (p: number, s: number, v: number) =>
  `/api/v1/projects/${p}/surveys/${s}/versions/${v}`;

// ── Questions ─────────────────────────────────────────────────────────────────

export function listQuestions(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
): Promise<QuestionOut[]> {
  return api.get<QuestionOut[]>(`${vBase(projectId, surveyId, versionId)}/questions`);
}

export function createQuestion(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  data: CreateQuestionRequest,
): Promise<QuestionOut> {
  return api.post<QuestionOut>(`${vBase(projectId, surveyId, versionId)}/questions`, data);
}

export function updateQuestion(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  questionId: number,
  data: UpdateQuestionRequest,
): Promise<QuestionOut> {
  return api.patch<QuestionOut>(
    `${vBase(projectId, surveyId, versionId)}/questions/${questionId}`,
    data,
  );
}

export function deleteQuestion(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  questionId: number,
): Promise<void> {
  return api.del(`${vBase(projectId, surveyId, versionId)}/questions/${questionId}`);
}

// ── Rules ─────────────────────────────────────────────────────────────────────

export function listRules(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
): Promise<RuleOut[]> {
  return api.get<RuleOut[]>(`${vBase(projectId, surveyId, versionId)}/rules`);
}

export function createRule(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  data: CreateRuleRequest,
): Promise<RuleOut> {
  return api.post<RuleOut>(`${vBase(projectId, surveyId, versionId)}/rules`, data);
}

export function updateRule(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  ruleId: number,
  data: UpdateRuleRequest,
): Promise<RuleOut> {
  return api.patch<RuleOut>(
    `${vBase(projectId, surveyId, versionId)}/rules/${ruleId}`,
    data,
  );
}

export function deleteRule(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  ruleId: number,
): Promise<void> {
  return api.del(`${vBase(projectId, surveyId, versionId)}/rules/${ruleId}`);
}

// ── Scoring Rules ─────────────────────────────────────────────────────────────

export function listScoringRules(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
): Promise<ScoringRuleOut[]> {
  return api.get<ScoringRuleOut[]>(`${vBase(projectId, surveyId, versionId)}/scoring-rules`);
}

export function createScoringRule(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  data: CreateScoringRuleRequest,
): Promise<ScoringRuleOut> {
  return api.post<ScoringRuleOut>(
    `${vBase(projectId, surveyId, versionId)}/scoring-rules`,
    data,
  );
}

export function updateScoringRule(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  scoringRuleId: number,
  data: UpdateScoringRuleRequest,
): Promise<ScoringRuleOut> {
  return api.patch<ScoringRuleOut>(
    `${vBase(projectId, surveyId, versionId)}/scoring-rules/${scoringRuleId}`,
    data,
  );
}

export function deleteScoringRule(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  versionId: number,
  scoringRuleId: number,
): Promise<void> {
  return api.del(`${vBase(projectId, surveyId, versionId)}/scoring-rules/${scoringRuleId}`);
}
