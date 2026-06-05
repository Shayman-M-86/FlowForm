import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
  MatchingPairIn,
} from "@flowform/schema";
import type {
  ChoiceRequirements,
  FieldDateOperator,
  FieldNumberOperator,
  RuleBranch,
  RuleCondition,
  RuleMatch,
} from "../../questionTypes";

export type QuestionNode = CreateQuestionNodeRequest;
export type RuleContent = CreateRuleNodeRequest["content"];

export type ChoiceMark = "none" | "required" | "forbidden" | "any_of";
export type DoKind = "skip_to" | "end_and_submit" | "end_and_discard";

/* ---------- Sibling lookup / option building (node_key based) ------------- */

export function questionOption(node: QuestionNode): { value: string; label: string } {
  const label = node.content.title?.trim() || node.content.label.trim() || node.node_key;
  return { value: node.node_key, label: `${label} (${node.node_key})` };
}

export function findSibling(
  siblings: QuestionNode[],
  targetId: string,
): QuestionNode | undefined {
  return siblings.find((node) => node.node_key === targetId);
}

/* ---------- Choice marks <-> ChoiceRequirements --------------------------- */

export function getChoiceMark(
  requirements: ChoiceRequirements,
  optionId: string,
): ChoiceMark {
  if (requirements.required?.includes(optionId)) return "required";
  if (requirements.forbidden?.includes(optionId)) return "forbidden";
  if (requirements.any_of?.includes(optionId)) return "any_of";
  return "none";
}

export function setChoiceMark(
  requirements: ChoiceRequirements,
  optionId: string,
  mark: ChoiceMark,
): ChoiceRequirements {
  const without = (items: string[] | undefined) => items?.filter((id) => id !== optionId);

  const next: ChoiceRequirements = {};
  const required = without(requirements.required);
  const forbidden = without(requirements.forbidden);
  const anyOf = without(requirements.any_of);
  if (required?.length) next.required = required;
  if (forbidden?.length) next.forbidden = forbidden;
  if (anyOf?.length) next.any_of = anyOf;

  if (mark !== "none") {
    next[mark] = [...(next[mark] ?? []), optionId];
  }

  return next;
}

/* ---------- Matching pairs ------------------------------------------------ */

export function getMatch(required: MatchingPairIn[], promptId: string): string {
  return required.find((pair) => pair.prompt_id === promptId)?.match_id ?? "";
}

export function setMatchingPair(
  required: MatchingPairIn[],
  promptId: string,
  matchId: string,
): MatchingPairIn[] {
  const withoutPrompt = required.filter((pair) => pair.prompt_id !== promptId);
  if (!matchId) return withoutPrompt;
  return [...withoutPrompt, { prompt_id: promptId, match_id: matchId }];
}

/* ---------- Default condition for a freshly targeted question ------------- */

export function createDefaultCondition(target: QuestionNode): RuleCondition {
  switch (target.content.family) {
    case "choice":
      return { target_id: target.node_key, family: "choice", requirements: {} };
    case "matching":
      return { target_id: target.node_key, family: "matching", requirements: { required: [] } };
    case "rating":
      return { target_id: target.node_key, family: "rating", requirements: {} };
    case "field":
      return target.content.definition.field_type === "date"
        ? {
            target_id: target.node_key,
            family: "field",
            requirements: { type: "date", operator: "before", value: "" },
          }
        : {
            target_id: target.node_key,
            family: "field",
            requirements: { type: "number", operator: "EQ", value: 0 },
          };
  }
}

/* ---------- Branch action helpers ----------------------------------------- */

export function doToKind(action: RuleBranch["do"] | null | undefined): DoKind {
  if (!action) return "skip_to";
  if ("skip_to" in action) return "skip_to";
  if ("end_and_submit" in action) return "end_and_submit";
  return "end_and_discard";
}

export function doToSkipTo(action: RuleBranch["do"] | null | undefined): string {
  return action && "skip_to" in action ? action.skip_to : "";
}

export function makeDo(kind: DoKind, skipTo: string): NonNullable<RuleBranch["do"]> {
  if (kind === "skip_to") return { skip_to: skipTo };
  if (kind === "end_and_submit") return { end_and_submit: true };
  return { end_and_discard: true };
}

/* ---------- Shared option arrays / style constants ------------------------ */

export const MATCH_OPTIONS: Array<{ value: RuleMatch; label: string }> = [
  { value: "ALL", label: "Match all" },
  { value: "ANY", label: "Match any" },
  { value: "NONE", label: "Match none" },
];

export const CHOICE_MARK_OPTIONS: Array<{
  value: ChoiceMark;
  label: string;
  rowActive: string;
  btnActive: string;
}> = [
  {
    value: "none",
    label: "Ignore",
    rowActive: "",
    btnActive: "bg-muted-foreground text-background border-transparent",
  },
  {
    value: "required",
    label: "Required",
    rowActive: "border-success/40 bg-success/10",
    btnActive: "bg-success text-background border-transparent",
  },
  {
    value: "forbidden",
    label: "Forbidden",
    rowActive: "border-destructive/40 bg-destructive/10",
    btnActive: "bg-destructive text-background border-transparent",
  },
  {
    value: "any_of",
    label: "Any of",
    rowActive: "border-warning/40 bg-warning/10",
    btnActive: "bg-warning text-background border-transparent",
  },
];

export const NUMBER_OP_OPTIONS: Array<{ value: FieldNumberOperator; label: string }> = [
  { value: "EQ", label: "Equals" },
  { value: "NEQ", label: "Not equal" },
  { value: "GT", label: "Greater than" },
  { value: "GTE", label: "Greater or equal" },
  { value: "LT", label: "Less than" },
  { value: "LTE", label: "Less or equal" },
];

export const DATE_OP_OPTIONS: Array<{ value: FieldDateOperator; label: string }> = [
  { value: "before", label: "Before" },
  { value: "after", label: "After" },
];

export const DO_OPTIONS: Array<{ value: DoKind; label: string }> = [
  { value: "skip_to", label: "Skip to" },
  { value: "end_and_submit", label: "End and submit" },
  { value: "end_and_discard", label: "End and discard" },
];

export const sectionClass = "border-t border-border pt-3 first:border-t-0 first:pt-0";
export const emptyTextClass = "m-0 px-4 py-2 text-[0.88rem] text-muted-foreground";
export const addBtnClass = "rounded-2xl min-h-11 mx-4 mb-3 mt-1.5";
export const choiceTagClass =
  "inline-flex items-center rounded-full border border-border bg-muted px-1.5 py-0.5 text-[0.72rem] font-bold uppercase text-muted-foreground";
export const pickerHeadClass = "flex items-baseline justify-between gap-2";
export const pickerTitleClass = "text-[0.95rem] font-semibold text-foreground";
export const pickerHintClass = "text-[0.78rem] uppercase tracking-[0.04em] text-muted-foreground";
export const toggleRowClass =
  "inline-flex items-center gap-1.5 whitespace-nowrap text-[0.85rem] text-muted-foreground";
