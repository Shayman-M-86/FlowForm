import type {
  ChoiceContent,
  FieldContent,
  QuestionContent,
  QuestionNode,
  RatingContent,
  RuleCondition,
  RuleSetEntry,
  SurveyNode,
} from "../node/questionTypes";

export type QuestionAnswer = string | string[] | number | Record<string, string> | null;
export type AnswerMap = Record<string, QuestionAnswer | undefined>;

export interface QuestionPresentationState {
  visible: boolean;
  required: boolean;
}

export type QuestionStateMap = Record<string, QuestionPresentationState>;

export interface PreparedSurvey {
  nodes: SurveyNode[];
  questionNodes: QuestionNode[];
  questionById: Map<string, QuestionContent>;
  questionIndexById: Map<string, number>;
}

export interface DerivedSurveyProgress {
  currentQuestionId: string | null;
  effectiveCommittedIds: string[];
  questionStateMap: QuestionStateMap;
  status: "active" | "submitted" | "discarded";
}

const DEFAULT_REQUIRED = true;

export function prepareSurvey(survey: SurveyNode[]): PreparedSurvey {
  const nodes = [...survey].sort((left, right) => left.sort_key - right.sort_key);
  const questionNodes = nodes.filter((node): node is QuestionNode => node.type === "question");
  const questionById = new Map(questionNodes.map((node) => [node.content.id, node.content] as const));
  const questionIndexById = new Map<string, number>();

  nodes.forEach((node, index) => {
    if (node.type === "question") {
      questionIndexById.set(node.content.id, index);
    }
  });

  return {
    nodes,
    questionNodes,
    questionById,
    questionIndexById,
  };
}

export function deriveSurveyProgress(
  preparedSurvey: PreparedSurvey,
  answers: AnswerMap,
  committedQuestionIds: string[],
): DerivedSurveyProgress {
  const questionStateMap = createQuestionStateMap(preparedSurvey.questionNodes);
  const effectiveCommittedIds: string[] = [];
  let cursor = 0;
  let safetyCounter = 0;

  while (cursor < preparedSurvey.nodes.length) {
    safetyCounter += 1;
    if (safetyCounter > (preparedSurvey.nodes.length * 4) + 8) {
      break;
    }

    const node = preparedSurvey.nodes[cursor];

    if (node.type === "question") {
      const state = questionStateMap[node.content.id];
      if (!state?.visible) {
        cursor += 1;
        continue;
      }

      const expectedCommittedId = committedQuestionIds[effectiveCommittedIds.length];
      if (expectedCommittedId === node.content.id) {
        effectiveCommittedIds.push(node.content.id);
        cursor += 1;
        continue;
      }

      return {
        currentQuestionId: node.content.id,
        effectiveCommittedIds,
        questionStateMap,
        status: "active",
      };
    }

    const ruleMatched = evaluateRuleMatch(node.content.if.match, node.content.if.conditions, answers);
    const nextSet = ruleMatched ? node.content.then.set : undefined;
    const nextAction = ruleMatched ? node.content.then.do : node.content.else?.do;

    applyQuestionStateUpdates(questionStateMap, nextSet);

    if (!nextAction) {
      cursor += 1;
      continue;
    }

    if ("skip_to" in nextAction) {
      const targetIndex = preparedSurvey.questionIndexById.get(nextAction.skip_to);
      cursor = targetIndex === undefined ? cursor + 1 : targetIndex;
      continue;
    }

    if ("end_and_submit" in nextAction && nextAction.end_and_submit) {
      return {
        currentQuestionId: null,
        effectiveCommittedIds,
        questionStateMap,
        status: "submitted",
      };
    }

    if ("end_and_discard" in nextAction && nextAction.end_and_discard) {
      return {
        currentQuestionId: null,
        effectiveCommittedIds,
        questionStateMap,
        status: "discarded",
      };
    }

    cursor += 1;
  }

  return {
    currentQuestionId: null,
    effectiveCommittedIds,
    questionStateMap,
    status: "submitted",
  };
}

export function validateQuestionAnswer(
  question: QuestionContent,
  answer: QuestionAnswer | undefined,
  required: boolean,
): string | null {
  switch (question.family) {
    case "choice":
      return validateChoiceAnswer(question, answer, required);
    case "matching":
      return validateMatchingAnswer(question, answer, required);
    case "rating":
      return validateRatingAnswer(question, answer, required);
    case "field":
      return validateFieldAnswer(question, answer, required);
    default:
      return null;
  }
}

function createQuestionStateMap(questionNodes: QuestionNode[]): QuestionStateMap {
  return Object.fromEntries(
    questionNodes.map((node) => [
      node.content.id,
      {
        visible: true,
        required: DEFAULT_REQUIRED,
      },
    ]),
  );
}

function applyQuestionStateUpdates(
  questionStateMap: QuestionStateMap,
  entries: RuleSetEntry[] | undefined,
) {
  if (!entries || entries.length === 0) return;

  entries.forEach((entry) => {
    const currentState = questionStateMap[entry.target_id];
    if (!currentState) return;

    questionStateMap[entry.target_id] = {
      visible: entry.visible ?? currentState.visible,
      required: entry.required ?? currentState.required,
    };
  });
}

function evaluateRuleMatch(
  match: "ALL" | "ANY" | "NONE",
  conditions: RuleCondition[],
  answers: AnswerMap,
): boolean {
  const results = conditions.map((condition) => evaluateRuleCondition(condition, answers[condition.source_id]));

  switch (match) {
    case "ANY":
      return results.some(Boolean);
    case "NONE":
      return results.every((result) => !result);
    case "ALL":
    default:
      return results.every(Boolean);
  }
}

function evaluateRuleCondition(
  condition: RuleCondition,
  answer: QuestionAnswer | undefined,
): boolean {
  switch (condition.family) {
    case "choice":
      return evaluateChoiceCondition(condition, answer);
    case "matching":
      return evaluateMatchingCondition(condition, answer);
    case "rating":
      return evaluateRatingCondition(condition, answer);
    case "field":
      return evaluateFieldCondition(condition, answer);
    default:
      return false;
  }
}

function evaluateChoiceCondition(
  condition: Extract<RuleCondition, { family: "choice" }>,
  answer: QuestionAnswer | undefined,
): boolean {
  const selections = Array.isArray(answer)
    ? answer.filter((value): value is string => typeof value === "string")
    : [];
  const requirements = condition.requirements;

  if (requirements.required && requirements.required.some((value) => !selections.includes(value))) {
    return false;
  }

  if (requirements.forbidden && requirements.forbidden.some((value) => selections.includes(value))) {
    return false;
  }

  if (requirements.any_of && requirements.any_of.length > 0) {
    return requirements.any_of.some((value) => selections.includes(value));
  }

  return true;
}

function evaluateMatchingCondition(
  condition: Extract<RuleCondition, { family: "matching" }>,
  answer: QuestionAnswer | undefined,
): boolean {
  const selections = asRecord(answer);
  const requiredPairs = condition.requirements.required ?? [];

  return requiredPairs.every((pair) =>
    Object.entries(pair).every(([promptId, matchId]) => selections[promptId] === matchId),
  );
}

function evaluateRatingCondition(
  condition: Extract<RuleCondition, { family: "rating" }>,
  answer: QuestionAnswer | undefined,
): boolean {
  if (typeof answer !== "number" || Number.isNaN(answer)) return false;

  const { min, max } = condition.requirements;
  if (min !== undefined && answer < min) return false;
  if (max !== undefined && answer > max) return false;
  return true;
}

function evaluateFieldCondition(
  condition: Extract<RuleCondition, { family: "field" }>,
  answer: QuestionAnswer | undefined,
): boolean {
  if (typeof answer !== "string") return false;

  const actualValue = answer.trim();
  if (actualValue === "") return false;

  if (condition.requirements.type === "date") {
    return compareDate(actualValue, condition.requirements.operator, condition.requirements.value);
  }

  return compareScalarValue(actualValue, condition.requirements.operator, condition.requirements.value);
}

function compareDate(actualValue: string, operator: "before" | "after", expectedValue: string): boolean {
  const actualTime = Date.parse(actualValue);
  const expectedTime = Date.parse(expectedValue);

  if (Number.isNaN(actualTime) || Number.isNaN(expectedTime)) {
    return false;
  }

  return operator === "before" ? actualTime < expectedTime : actualTime > expectedTime;
}

function compareScalarValue(
  actualValue: string,
  operator: "LT" | "LTE" | "GT" | "GTE" | "EQ" | "NEQ",
  expectedValue: number | string,
): boolean {
  const normalizedExpected = String(expectedValue).trim();
  const actualNumber = Number(actualValue);
  const expectedNumber = Number(normalizedExpected);
  const useNumericComparison =
    actualValue !== "" &&
    normalizedExpected !== "" &&
    Number.isFinite(actualNumber) &&
    Number.isFinite(expectedNumber);

  if (!useNumericComparison && operator !== "EQ" && operator !== "NEQ") {
    switch (operator) {
      case "LT":
        return actualValue < normalizedExpected;
      case "LTE":
        return actualValue <= normalizedExpected;
      case "GT":
        return actualValue > normalizedExpected;
      case "GTE":
        return actualValue >= normalizedExpected;
      default:
        return false;
    }
  }

  if (!useNumericComparison) {
    return operator === "EQ" ? actualValue === normalizedExpected : actualValue !== normalizedExpected;
  }

  switch (operator) {
    case "LT":
      return actualNumber < expectedNumber;
    case "LTE":
      return actualNumber <= expectedNumber;
    case "GT":
      return actualNumber > expectedNumber;
    case "GTE":
      return actualNumber >= expectedNumber;
    case "EQ":
      return actualNumber === expectedNumber;
    case "NEQ":
      return actualNumber !== expectedNumber;
    default:
      return false;
  }
}

function validateChoiceAnswer(
  question: ChoiceContent,
  answer: QuestionAnswer | undefined,
  required: boolean,
): string | null {
  const selections = Array.isArray(answer)
    ? answer.filter((value): value is string => typeof value === "string")
    : [];

  if (selections.length === 0) {
    return required ? "Select at least one option before continuing." : null;
  }

  if (selections.length < question.definition.min) {
    return `Select at least ${question.definition.min} option${question.definition.min === 1 ? "" : "s"}.`;
  }

  if (selections.length > question.definition.max) {
    return `Select no more than ${question.definition.max} option${question.definition.max === 1 ? "" : "s"}.`;
  }

  return null;
}

function validateMatchingAnswer(
  question: Extract<QuestionContent, { family: "matching" }>,
  answer: QuestionAnswer | undefined,
  required: boolean,
): string | null {
  const selections = asRecord(answer);
  const filledCount = question.definition.prompts.filter((prompt) => selections[prompt.id]).length;

  if (filledCount === 0) {
    return required ? "Match each prompt before continuing." : null;
  }

  if (filledCount !== question.definition.prompts.length) {
    return "Complete every match before continuing.";
  }

  return null;
}

function validateRatingAnswer(
  question: RatingContent,
  answer: QuestionAnswer | undefined,
  required: boolean,
): string | null {
  if (typeof answer !== "number" || Number.isNaN(answer)) {
    return required ? "Choose a rating before continuing." : null;
  }

  switch (question.definition.variant) {
    case "slider":
      if (answer < question.definition.range.min || answer > question.definition.range.max) {
        return "Choose a rating within the available range.";
      }
      return null;
    case "emoji":
      if (answer < 1 || answer > 5) {
        return "Choose one emoji before continuing.";
      }
      return null;
    case "star":
      if (answer < 1 || answer > question.definition.stars) {
        return "Choose a valid star rating before continuing.";
      }
      return null;
    default:
      return null;
  }
}

function validateFieldAnswer(
  question: FieldContent,
  answer: QuestionAnswer | undefined,
  required: boolean,
): string | null {
  const value = typeof answer === "string" ? answer.trim() : "";

  if (value === "") {
    return required ? "Enter a response before continuing." : null;
  }

  switch (question.definition.field_type) {
    case "email":
      return /\S+@\S+\.\S+/.test(value) ? null : "Enter a valid email address.";
    case "phone":
      return /^[0-9()+\-\s]{7,}$/.test(value) ? null : "Enter a valid phone number.";
    case "number":
      return Number.isFinite(Number(value)) ? null : "Enter a valid number.";
    case "date":
      return Number.isNaN(Date.parse(value)) ? "Choose a valid date." : null;
    default:
      return null;
  }
}

function asRecord(answer: QuestionAnswer | undefined): Record<string, string> {
  if (!answer || typeof answer !== "object" || Array.isArray(answer)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(answer).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
  );
}
