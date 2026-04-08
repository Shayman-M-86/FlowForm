import { del, get, patch, post } from "./client";
import type {
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
  projectId: number,
  surveyId: number,
  versionId: number,
): Promise<QuestionOut[]> {
  return get(`${vBase(projectId, surveyId, versionId)}/questions`);
}

export function createQuestion(
  projectId: number,
  surveyId: number,
  versionId: number,
  data: CreateQuestionRequest,
): Promise<QuestionOut> {
  return post(`${vBase(projectId, surveyId, versionId)}/questions`, data);
}

export function updateQuestion(
  projectId: number,
  surveyId: number,
  versionId: number,
  questionId: number,
  data: UpdateQuestionRequest,
): Promise<QuestionOut> {
  return patch(
    `${vBase(projectId, surveyId, versionId)}/questions/${questionId}`,
    data,
  );
}

export function deleteQuestion(
  projectId: number,
  surveyId: number,
  versionId: number,
  questionId: number,
): Promise<void> {
  return del(`${vBase(projectId, surveyId, versionId)}/questions/${questionId}`);
}

// ── Rules ─────────────────────────────────────────────────────────────────────

export function listRules(
  projectId: number,
  surveyId: number,
  versionId: number,
): Promise<RuleOut[]> {
  return get(`${vBase(projectId, surveyId, versionId)}/rules`);
}

export function createRule(
  projectId: number,
  surveyId: number,
  versionId: number,
  data: CreateRuleRequest,
): Promise<RuleOut> {
  return post(`${vBase(projectId, surveyId, versionId)}/rules`, data);
}

export function updateRule(
  projectId: number,
  surveyId: number,
  versionId: number,
  ruleId: number,
  data: UpdateRuleRequest,
): Promise<RuleOut> {
  return patch(
    `${vBase(projectId, surveyId, versionId)}/rules/${ruleId}`,
    data,
  );
}

export function deleteRule(
  projectId: number,
  surveyId: number,
  versionId: number,
  ruleId: number,
): Promise<void> {
  return del(`${vBase(projectId, surveyId, versionId)}/rules/${ruleId}`);
}

// ── Scoring Rules ─────────────────────────────────────────────────────────────

export function listScoringRules(
  projectId: number,
  surveyId: number,
  versionId: number,
): Promise<ScoringRuleOut[]> {
  return get(`${vBase(projectId, surveyId, versionId)}/scoring-rules`);
}

export function createScoringRule(
  projectId: number,
  surveyId: number,
  versionId: number,
  data: CreateScoringRuleRequest,
): Promise<ScoringRuleOut> {
  return post(`${vBase(projectId, surveyId, versionId)}/scoring-rules`, data);
}

export function updateScoringRule(
  projectId: number,
  surveyId: number,
  versionId: number,
  scoringRuleId: number,
  data: UpdateScoringRuleRequest,
): Promise<ScoringRuleOut> {
  return patch(
    `${vBase(projectId, surveyId, versionId)}/scoring-rules/${scoringRuleId}`,
    data,
  );
}

export function deleteScoringRule(
  projectId: number,
  surveyId: number,
  versionId: number,
  scoringRuleId: number,
): Promise<void> {
  return del(
    `${vBase(projectId, surveyId, versionId)}/scoring-rules/${scoringRuleId}`,
  );
}
