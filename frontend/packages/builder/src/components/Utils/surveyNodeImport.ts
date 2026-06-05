import { type ZodIssue } from "zod";
import {
  CreateQuestionNodeRequestSchema,
  CreateRuleNodeRequestSchema,
  type ChoiceQuestionSchemaIn,
  type CreateQuestionNodeRequest,
  type FieldQuestionSchemaIn,
  type MatchingQuestionSchemaIn,
  type RatingQuestionSchemaIn,
  type RuleBranchIn,
  type RuleSchemaIn,
} from "@flowform/schema";
import type { SurveyNode } from "../node/questionTypes";

export interface SurveyNodeImportIssue {
  path: string;
  message: string;
  nodeIndex: number | null;
}

export class SurveyNodeImportError extends Error {
  issues: SurveyNodeImportIssue[];
  nodeIndex: number | null;

  constructor(issues: SurveyNodeImportIssue[]) {
    const first = issues[0];
    super(
      first
        ? `${first.path}: ${first.message}`
        : "Invalid survey node import.",
    );
    this.name = "SurveyNodeImportError";
    this.issues = issues;
    this.nodeIndex = first?.nodeIndex ?? null;
  }
}

type QuestionContent =
  | ChoiceQuestionSchemaIn
  | FieldQuestionSchemaIn
  | MatchingQuestionSchemaIn
  | RatingQuestionSchemaIn;

type QuestionIndex = {
  content: QuestionContent;
  sortKey: number;
};

type IndexedNode = {
  node: SurveyNode;
  nodeIndex: number;
};

const IMPORT_NODES_MAX = 500;
const IMPORT_JSON_BYTES_MAX = 1_000_000;

export function parseSurveyNodeJson(rawJson: string): SurveyNode[] {
  const normalizedJson = stripJsonFence(rawJson);

  if (new TextEncoder().encode(normalizedJson).length > IMPORT_JSON_BYTES_MAX) {
    throwImport([{
      path: "$",
      message: "The imported JSON exceeds the 1 MB size limit.",
      nodeIndex: null,
    }]);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(normalizedJson);
  } catch (e) {
    const location = e instanceof SyntaxError ? locateJsonError(e) : null;
    const suffix = location ? ` (line ${location.line}, col ${location.col})` : "";
    throwImport([{
      path: "$",
      message: `Invalid JSON${suffix}. Paste a raw JSON array of survey nodes.`,
      nodeIndex: null,
    }]);
  }

  return importSurveyNodes(parsed);
}

export function importSurveyNodes(input: unknown): SurveyNode[] {
  if (!Array.isArray(input)) {
    throwImport([{ path: "$", message: "Expected a JSON array of survey nodes.", nodeIndex: null }]);
  }
  if (input.length === 0) {
    throwImport([{ path: "$", message: "Expected at least one survey node.", nodeIndex: null }]);
  }
  if (input.length > IMPORT_NODES_MAX) {
    throwImport([{ path: "$", message: `Expected at most ${IMPORT_NODES_MAX} nodes, got ${input.length}.`, nodeIndex: null }]);
  }

  // Pass 1: parse individual node shapes. Collect all parse errors before proceeding.
  const issues: SurveyNodeImportIssue[] = [];
  const indexedNodes: IndexedNode[] = [];

  input.forEach((value, nodeIndex) => {
    const node = parseNode(value, nodeIndex, issues);
    if (node) {
      indexedNodes.push({ node, nodeIndex });
    }
  });

  throwIfIssues(issues);

  // Pass 2: validate graph identity (IDs, sort keys). Must succeed before reference checks
  // because duplicate IDs make references ambiguous.
  const questionById = validateGraphIdentity(indexedNodes, issues);
  throwIfIssues(issues);

  // Pass 3: validate cross-node references.
  validateRuleReferences(indexedNodes, questionById, issues);
  throwIfIssues(issues);

  return indexedNodes.map(({ node }) => node);
}

export function safeImportSurveyNodes(
  input: unknown,
): { ok: true; nodes: SurveyNode[] } | { ok: false; error: SurveyNodeImportError } {
  try {
    return { ok: true, nodes: importSurveyNodes(input) };
  } catch (error) {
    if (error instanceof SurveyNodeImportError) {
      return { ok: false, error };
    }
    throw error;
  }
}

export function findNodeLine(rawJson: string, nodeIndex: number | null): number | null {
  if (nodeIndex === null) return null;
  try {
    let depth = 0;
    let found = 0;
    let inString = false;
    let escape = false;
    for (let pos = 0; pos < rawJson.length; pos++) {
      const ch = rawJson[pos];
      if (escape) { escape = false; continue; }
      if (ch === "\\" && inString) { escape = true; continue; }
      if (ch === "\"") { inString = !inString; continue; }
      if (inString) continue;
      if (ch === "{" || ch === "[") {
        depth++;
        if (depth === 2 && ch === "{") {
          if (found === nodeIndex) return rawJson.slice(0, pos).split("\n").length;
          found++;
        }
      } else if (ch === "}" || ch === "]") {
        depth--;
      }
    }
  } catch {
    return null;
  }
  return null;
}

function parseNode(
  value: unknown,
  nodeIndex: number,
  issues: SurveyNodeImportIssue[],
): SurveyNode | null {
  const path = `$[${nodeIndex}]`;
  const normalized = normalizeNode(value, nodeIndex, issues);

  if (!isRecord(normalized)) {
    pushIssue(issues, path, "Expected an object.", nodeIndex);
    return null;
  }

  const schema =
    normalized.node_type === "question"
      ? CreateQuestionNodeRequestSchema
      : normalized.node_type === "rule"
        ? CreateRuleNodeRequestSchema
        : null;

  if (!schema) {
    const got = normalized.node_type === undefined ? "missing" : `"${String(normalized.node_type)}"`;
    pushIssue(
      issues,
      `${path}.node_type`,
      `Expected "question" or "rule", got ${got}.`,
      nodeIndex,
    );
    return null;
  }

  const parsed = schema.safeParse(normalized);

  if (!parsed.success) {
    for (const issue of parsed.error.issues) {
      issues.push({
        path: formatZodPath(path, issue.path),
        message: annotateZodMessage(issue),
        nodeIndex,
      });
    }
    return null;
  }

  return parsed.data as SurveyNode;
}

function normalizeNode(
  value: unknown,
  nodeIndex: number,
  issues: SurveyNodeImportIssue[],
): unknown {
  if (!isRecord(value)) return value;

  const path = `$[${nodeIndex}]`;
  // Accept legacy aliases ("type" -> node_type, "question_schema" -> content)
  // and forward them to the canonical generated shape.
  const { type, question_schema, ...rest } = value;

  if (type !== undefined && rest.node_type !== undefined && type !== rest.node_type) {
    pushIssue(
      issues,
      `${path}.node_type`,
      `Conflicting values: "type" is "${String(type)}" but "node_type" is "${String(rest.node_type)}". Remove one.`,
      nodeIndex,
    );
  }

  if (rest.content !== undefined && question_schema !== undefined) {
    pushIssue(
      issues,
      `${path}.content`,
      `Conflicting fields: provide either "content" or "question_schema", not both.`,
      nodeIndex,
    );
  }

  return {
    ...rest,
    node_type: rest.node_type ?? type,
    content: rest.content ?? question_schema,
  };
}

function validateGraphIdentity(
  nodes: IndexedNode[],
  issues: SurveyNodeImportIssue[],
): Map<string, QuestionIndex> {
  const nodeKeys = new Map<string, number>();
  const nodeIds = new Map<number, number>();
  const sortKeys = new Map<number, number>();
  const questionById = new Map<string, QuestionIndex>();

  for (const { node, nodeIndex } of nodes) {
    const path = `$[${nodeIndex}]`;
    const nodeKey = node.node_key;

    const previousKeyIndex = nodeKeys.get(nodeKey);
    if (previousKeyIndex !== undefined) {
      pushIssue(
        issues,
        `${path}.node_key`,
        `Duplicate node_key "${nodeKey}" — already used by node at index ${previousKeyIndex}.`,
        nodeIndex,
      );
    } else {
      nodeKeys.set(nodeKey, nodeIndex);
      if (node.node_type === "question") {
        questionById.set(nodeKey, { content: node.content, sortKey: node.sort_key });
      }
    }

    // `id` is the immutable row identity ((survey_version_id, id) on the
    // backend); a collision would silently overwrite another node on save.
    const previousIdIndex = nodeIds.get(node.id);
    if (previousIdIndex !== undefined) {
      pushIssue(
        issues,
        `${path}.id`,
        `Duplicate id ${node.id} — already used by node at index ${previousIdIndex}.`,
        nodeIndex,
      );
    } else {
      nodeIds.set(node.id, nodeIndex);
    }

    const previousSortIndex = sortKeys.get(node.sort_key);
    if (previousSortIndex !== undefined) {
      pushIssue(
        issues,
        `${path}.sort_key`,
        `Duplicate sort_key ${node.sort_key} — already used by node at index ${previousSortIndex}.`,
        nodeIndex,
      );
    } else {
      sortKeys.set(node.sort_key, nodeIndex);
    }

    if (node.node_type === "question") {
      validateQuestionContent(node.content, path, nodeIndex, issues);
    }
  }

  return questionById;
}

function validateRuleReferences(
  nodes: IndexedNode[],
  questionById: Map<string, QuestionIndex>,
  issues: SurveyNodeImportIssue[],
) {
  for (const { node, nodeIndex } of nodes) {
    if (node.node_type === "rule") {
      validateRuleContent(node.content, node.sort_key, nodeIndex, questionById, issues);
    }
  }
}

function validateQuestionContent(
  content: CreateQuestionNodeRequest["content"],
  path: string,
  nodeIndex: number,
  issues: SurveyNodeImportIssue[],
) {
  if (content.family === "choice") {
    if (content.definition.options.length === 0) {
      pushIssue(issues, `${path}.content.definition.options`, "Choice questions require at least one option.", nodeIndex);
    }
    if (content.definition.min > content.definition.max) {
      pushIssue(issues, `${path}.content.definition.min`, `min (${content.definition.min}) cannot be greater than max (${content.definition.max}).`, nodeIndex);
    }
    if (content.definition.max > content.definition.options.length) {
      pushIssue(issues, `${path}.content.definition.max`, `max (${content.definition.max}) cannot exceed the number of options (${content.definition.options.length}).`, nodeIndex);
    }
    validateUniqueValues(
      content.definition.options.map((option) => option.id),
      `${path}.content.definition.options`,
      "option id",
      nodeIndex,
      issues,
    );
  }

  if (content.family === "matching") {
    if (content.definition.prompts.length === 0) {
      pushIssue(issues, `${path}.content.definition.prompts`, "Matching questions require at least one prompt.", nodeIndex);
    }
    if (content.definition.matches.length === 0) {
      pushIssue(issues, `${path}.content.definition.matches`, "Matching questions require at least one match.", nodeIndex);
    }
    validateUniqueValues(
      content.definition.prompts.map((prompt) => prompt.id),
      `${path}.content.definition.prompts`,
      "prompt id",
      nodeIndex,
      issues,
    );
    validateUniqueValues(
      content.definition.matches.map((match) => match.id),
      `${path}.content.definition.matches`,
      "match id",
      nodeIndex,
      issues,
    );
  }

  if (content.family === "rating" && content.definition.variant === "slider") {
    const { min, max, step } = content.definition.range;
    if (min >= max) {
      pushIssue(issues, `${path}.content.definition.range.max`, `Slider max (${max}) must be greater than min (${min}).`, nodeIndex);
    }
    if (step <= 0) {
      pushIssue(issues, `${path}.content.definition.range.step`, `Slider step (${step}) must be greater than 0.`, nodeIndex);
    }
  }
}

function validateRuleContent(
  rule: RuleSchemaIn,
  ruleSortKey: number,
  nodeIndex: number,
  questionById: Map<string, QuestionIndex>,
  issues: SurveyNodeImportIssue[],
) {
  rule.if.conditions.forEach((condition, conditionIndex) => {
    const path = `$[${nodeIndex}].content.if.conditions[${conditionIndex}]`;
    const target = questionById.get(condition.target_id);

    if (!target) {
      const validKeys = [...questionById.keys()].join(", ");
      pushIssue(issues, `${path}.target_id`, `Condition target "${condition.target_id}" does not match any question node_key. Valid node_keys are: ${validKeys}.`, nodeIndex);
      return;
    }
    if (target.sortKey >= ruleSortKey) {
      pushIssue(issues, `${path}.target_id`, `Condition target "${condition.target_id}" has sort_key ${target.sortKey}, which is not before this rule's sort_key ${ruleSortKey}. Rule conditions can only reference earlier question nodes.`, nodeIndex);
    }
    if (target.content.family !== condition.family) {
      pushIssue(issues, `${path}.family`, `Condition family "${condition.family}" does not match target question family "${target.content.family}".`, nodeIndex);
      return;
    }

    validateConditionTargetValues(condition, target.content, path, nodeIndex, issues);
  });

  validateBranchReferences(rule.then, ruleSortKey, `$[${nodeIndex}].content.then`, nodeIndex, questionById, issues);
  if (rule.else) {
    validateBranchReferences(rule.else, ruleSortKey, `$[${nodeIndex}].content.else`, nodeIndex, questionById, issues);
  }
}

function validateConditionTargetValues(
  condition: RuleSchemaIn["if"]["conditions"][number],
  target: QuestionContent,
  path: string,
  nodeIndex: number,
  issues: SurveyNodeImportIssue[],
) {
  if (condition.family === "choice" && target.family === "choice") {
    const optionIds = new Set(target.definition.options.map((option) => option.id));

    for (const key of ["required", "forbidden", "any_of"] as const) {
      condition.requirements[key]?.forEach((optionId, optionIndex) => {
        if (!optionIds.has(optionId)) {
          pushIssue(
            issues,
            `${path}.requirements.${key}[${optionIndex}]`,
            `Unknown choice option id "${optionId}". Valid ids are: ${[...optionIds].join(", ")}.`,
            nodeIndex,
          );
        }
      });
    }

    const required = new Set(condition.requirements.required ?? []);
    const forbidden = new Set(condition.requirements.forbidden ?? []);
    for (const optionId of required) {
      if (forbidden.has(optionId)) {
        pushIssue(
          issues,
          `${path}.requirements`,
          `Choice option "${optionId}" appears in both "required" and "forbidden" — these are mutually exclusive.`,
          nodeIndex,
        );
      }
    }
  }

  if (condition.family === "matching" && target.family === "matching") {
    const promptIds = new Set(target.definition.prompts.map((prompt) => prompt.id));
    const matchIds = new Set(target.definition.matches.map((match) => match.id));
    condition.requirements.required.forEach((pair, pairIndex) => {
      if (!promptIds.has(pair.prompt_id)) {
        pushIssue(
          issues,
          `${path}.requirements.required[${pairIndex}].prompt_id`,
          `Unknown matching prompt id "${pair.prompt_id}". Valid ids are: ${[...promptIds].join(", ")}.`,
          nodeIndex,
        );
      }
      if (!matchIds.has(pair.match_id)) {
        pushIssue(
          issues,
          `${path}.requirements.required[${pairIndex}].match_id`,
          `Unknown matching match id "${pair.match_id}". Valid ids are: ${[...matchIds].join(", ")}.`,
          nodeIndex,
        );
      }
    });
  }

  if (condition.family === "rating" && target.family === "rating") {
    const bounds = getRatingBounds(target);
    const { min, max } = condition.requirements;

    if (min != null && max != null && min > max) {
      pushIssue(
        issues,
        `${path}.requirements`,
        `Condition min (${min}) cannot be greater than condition max (${max}).`,
        nodeIndex,
      );
    }
    if (min != null && min < bounds.min) {
      pushIssue(issues, `${path}.requirements.min`, `Rating min (${min}) cannot be less than the question's minimum (${bounds.min}).`, nodeIndex);
    }
    if (max != null && max > bounds.max) {
      pushIssue(issues, `${path}.requirements.max`, `Rating max (${max}) cannot be greater than the question's maximum (${bounds.max}).`, nodeIndex);
    }
  }

  if (condition.family === "field" && target.family === "field") {
    if (condition.requirements.type === "number" && target.definition.field_type !== "number") {
      pushIssue(issues, `${path}.requirements.type`, `Number field requirements can only target "number" fields, but target "${condition.target_id}" is a "${target.definition.field_type}" field.`, nodeIndex);
    }
    if (condition.requirements.type === "date" && target.definition.field_type !== "date") {
      pushIssue(issues, `${path}.requirements.type`, `Date field requirements can only target "date" fields, but target "${condition.target_id}" is a "${target.definition.field_type}" field.`, nodeIndex);
    }
  }
}

function validateBranchReferences(
  branch: RuleBranchIn,
  ruleSortKey: number,
  path: string,
  nodeIndex: number,
  questionById: Map<string, QuestionIndex>,
  issues: SurveyNodeImportIssue[],
) {
  if (!branch.set && !branch.do) {
    pushIssue(issues, path, "Rule branch must include either \"set\" or \"do\".", nodeIndex);
  }
  if (branch.set && branch.do) {
    pushIssue(issues, path, "Rule branch cannot include both \"set\" and \"do\" — use one or the other.", nodeIndex);
  }

  if (branch.set) {
    validateUniqueValues(
      branch.set.map((entry) => entry.target_id),
      `${path}.set`,
      "target_id",
      nodeIndex,
      issues,
      "target_id",
    );

    branch.set.forEach((entry, entryIndex) => {
      validateFutureQuestionReference(entry.target_id, `${path}.set[${entryIndex}].target_id`, ruleSortKey, nodeIndex, questionById, issues);
      if (entry.visible === undefined && entry.required === undefined) {
        pushIssue(issues, `${path}.set[${entryIndex}]`, "Set entry must include at least one of \"visible\" or \"required\".", nodeIndex);
      }
    });
  }

  if (branch.do && "skip_to" in branch.do) {
    validateFutureQuestionReference(branch.do.skip_to, `${path}.do.skip_to`, ruleSortKey, nodeIndex, questionById, issues);
  }
}

function validateFutureQuestionReference(
  targetId: string,
  path: string,
  ruleSortKey: number,
  nodeIndex: number,
  questionById: Map<string, QuestionIndex>,
  issues: SurveyNodeImportIssue[],
) {
  const target = questionById.get(targetId);
  if (!target) {
    const validKeys = [...questionById.keys()].join(", ");
    pushIssue(issues, path, `Target "${targetId}" does not match any question node_key. Valid node_keys are: ${validKeys}.`, nodeIndex);
    return;
  }
  if (target.sortKey <= ruleSortKey) {
    pushIssue(issues, path, `Target "${targetId}" has sort_key ${target.sortKey}, which is not after this rule's sort_key ${ruleSortKey}. Rule actions can only reference later question nodes.`, nodeIndex);
  }
}

function validateUniqueValues(
  values: string[],
  path: string,
  label: string,
  nodeIndex: number,
  issues: SurveyNodeImportIssue[],
  property = "id",
) {
  const seen = new Set<string>();
  values.forEach((value, valueIndex) => {
    if (seen.has(value)) {
      pushIssue(issues, `${path}[${valueIndex}].${property}`, `Duplicate ${label} "${value}".`, nodeIndex);
    }
    seen.add(value);
  });
}

function getRatingBounds(content: RatingQuestionSchemaIn): { min: number; max: number } {
  switch (content.definition.variant) {
    case "slider":
      return { min: content.definition.range.min, max: content.definition.range.max };
    case "stars":
      return { min: 1, max: content.definition.stars };
    case "emoji":
      return { min: 1, max: 5 };
  }
}

function formatZodPath(basePath: string, parts: PropertyKey[]): string {
  return parts.reduce<string>((path, part) => {
    return typeof part === "number" ? `${path}[${part}]` : `${path}.${String(part)}`;
  }, basePath);
}

function pushIssue(
  issues: SurveyNodeImportIssue[],
  path: string,
  message: string,
  nodeIndex: number | null,
) {
  issues.push({ path, message, nodeIndex });
}

function throwIfIssues(issues: SurveyNodeImportIssue[]): void {
  if (issues.length > 0) throwImport(issues);
}

function throwImport(issues: SurveyNodeImportIssue[]): never {
  throw new SurveyNodeImportError(issues);
}

function annotateZodMessage(issue: ZodIssue): string {
  if (issue.code === "invalid_type") {
    return `${issue.message} (received ${issue.received})`;
  }
  if (issue.code === "invalid_literal") {
    return `${issue.message} (received ${JSON.stringify(issue.received)})`;
  }
  return issue.message;
}

function locateJsonError(e: SyntaxError): { line: number; col: number } | null {
  // V8 (Chrome/Node): "... at position N (line L column C)"
  const lineCol = /\(line (\d+) column (\d+)\)/.exec(e.message);
  if (lineCol) return { line: parseInt(lineCol[1], 10), col: parseInt(lineCol[2], 10) };
  // Older V8 / other engines: "... at position N" (char offset into the source)
  const pos = /\bposition (\d+)/.exec(e.message);
  if (pos) {
    const offset = parseInt(pos[1], 10);
    // offset is into the source, not the message — but we don't have the source here;
    // just surface the char offset directly so the user has something.
    return { line: 1, col: offset + 1 };
  }
  return null;
}

function stripJsonFence(rawJson: string): string {
  return rawJson.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
