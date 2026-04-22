import { useEffect, useMemo, useState, forwardRef, useImperativeHandle } from "react";
import {
  NodePillTopbar,
  NodePillFieldHead,
  NodePillCollapsed,
} from "./NodePillShell";
import {
  nodePillBodyClass,
  nodePillFieldClass,
  nodePillShellClass,
  nodePillShellEditClass,
} from "./nodePillStyles";
import { Card } from "../ui/Card";
import { CardStack } from "../ui/CardStack";
import { Select } from "../ui/Select";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { NumberStepper } from "../ui/NumberStepper";
import type {
  QuestionContent,
  ChoiceContent,
  MatchingContent,
  RatingContent,
  FieldContent,
  RuleContent,
  RuleMatch,
  RuleCondition,
  ChoiceRequirements,
  MatchingRequirements,
  RatingRequirements,
  FieldRequirements,
  FieldNumberOperator,
  FieldDateOperator,
  RuleSetEntry,
  RuleDoAction,
} from "./questionTypes";

export interface RulesQuestionHandle {
  getData(): RuleContent;
}

interface RulesQuestionProps {
  onDelete?: () => void;
  title?: string;
  initialTag?: string;
  initialContent?: RuleContent;
  idError?: string;
  isCollapsed?: boolean;
  onExpand?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (content: RuleContent) => void;
  previousSiblings?: QuestionContent[];
  followingSiblings?: QuestionContent[];
}

type ChoiceMark = "none" | "required" | "forbidden" | "any_of";

type ConditionDraft =
  | { key: string; target_id: string; family: "choice"; marks: Record<string, ChoiceMark> }
  | { key: string; target_id: string; family: "matching"; pairs: Record<string, string> }
  | { key: string; target_id: string; family: "rating"; min: number | null; max: number | null }
  | {
      key: string;
      target_id: string;
      family: "field";
      numberOperator: FieldNumberOperator;
      numberValue: string;
      dateOperator: FieldDateOperator;
      dateValue: string;
    }
  | { key: string; target_id: ""; family: null };

type ThenMode = "set" | "do";
type DoKind = "skip_to" | "end_and_submit" | "end_and_discard";

const MATCH_OPTIONS: Array<{ value: RuleMatch; label: string }> = [
  { value: "ALL", label: "Match all" },
  { value: "ANY", label: "Match any" },
  { value: "NONE", label: "Match none" },
];

const CHOICE_MARK_OPTIONS: Array<{
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

const NUMBER_OP_OPTIONS: Array<{ value: FieldNumberOperator; label: string }> = [
  { value: "EQ", label: "Equals" },
  { value: "NEQ", label: "Not equal" },
  { value: "GT", label: "Greater than" },
  { value: "GTE", label: "Greater or equal" },
  { value: "LT", label: "Less than" },
  { value: "LTE", label: "Less or equal" },
];

const DATE_OP_OPTIONS: Array<{ value: FieldDateOperator; label: string }> = [
  { value: "before", label: "Before" },
  { value: "after", label: "After" },
];

const DO_OPTIONS: Array<{ value: DoKind; label: string }> = [
  { value: "skip_to", label: "Skip to" },
  { value: "end_and_submit", label: "End and submit" },
  { value: "end_and_discard", label: "End and discard" },
];

let conditionCounter = 0;
function newConditionKey() {
  conditionCounter += 1;
  return `cond_${conditionCounter}`;
}

let setEntryCounter = 0;
function newSetEntryKey() {
  setEntryCounter += 1;
  return `set_${setEntryCounter}`;
}

function questionOption(content: QuestionContent) {
  const label = content.title.trim() || content.label.trim() || content.id;
  return { value: content.id, label: `${label} (${content.id})` };
}

function buildConditionFromTarget(
  target: QuestionContent,
  key: string = newConditionKey(),
): ConditionDraft {
  switch (target.family) {
    case "choice": {
      const marks: Record<string, ChoiceMark> = {};
      target.definition.options.forEach((opt) => {
        marks[opt.id] = "none";
      });
      return { key, target_id: target.id, family: "choice", marks };
    }
    case "matching": {
      const pairs: Record<string, string> = {};
      target.definition.prompts.forEach((p) => {
        pairs[p.id] = "";
      });
      return { key, target_id: target.id, family: "matching", pairs };
    }
    case "rating":
      return { key, target_id: target.id, family: "rating", min: null, max: null };
    case "field":
      return {
        key,
        target_id: target.id,
        family: "field",
        numberOperator: "EQ",
        numberValue: "",
        dateOperator: "before",
        dateValue: "",
      };
  }
}

function draftToCondition(draft: ConditionDraft, target: QuestionContent | undefined): RuleCondition | null {
  if (draft.family === null || !draft.target_id) return null;

  if (draft.family === "choice") {
    const reqs: ChoiceRequirements = {};
    const required: string[] = [];
    const forbidden: string[] = [];
    const anyOf: string[] = [];
    Object.entries(draft.marks).forEach(([optId, mark]) => {
      if (mark === "required") required.push(optId);
      else if (mark === "forbidden") forbidden.push(optId);
      else if (mark === "any_of") anyOf.push(optId);
    });
    if (required.length) reqs.required = required;
    if (forbidden.length) reqs.forbidden = forbidden;
    if (anyOf.length) reqs.any_of = anyOf;
    return { source_id: draft.target_id, family: "choice", requirements: reqs };
  }

  if (draft.family === "matching") {
    const required: Array<Record<string, string>> = [];
    Object.entries(draft.pairs).forEach(([promptId, matchId]) => {
      if (matchId) required.push({ [promptId]: matchId });
    });
    const reqs: MatchingRequirements = required.length ? { required } : {};
    return { source_id: draft.target_id, family: "matching", requirements: reqs };
  }

  if (draft.family === "rating") {
    const reqs: RatingRequirements = {};
    if (draft.min !== null) reqs.min = draft.min;
    if (draft.max !== null) reqs.max = draft.max;
    return { source_id: draft.target_id, family: "rating", requirements: reqs };
  }

  const fieldTarget = target && target.family === "field" ? target : null;
  const fieldType = fieldTarget?.definition.field_type ?? "short_text";
  let requirements: FieldRequirements;
  if (fieldType === "date") {
    requirements = { type: "date", operator: draft.dateOperator, value: draft.dateValue };
  } else {
    const isNumber = fieldType === "number";
    const value: number | string = isNumber
      ? draft.numberValue === "" ? "" : Number(draft.numberValue)
      : draft.numberValue;
    requirements = { type: fieldType, operator: draft.numberOperator, value };
  }
  return { source_id: draft.target_id, family: "field", requirements };
}

function findSibling(siblings: QuestionContent[], id: string) {
  return siblings.find((s) => s.id === id);
}

function doToState(action: RuleDoAction | undefined): { kind: DoKind; skipTo: string } {
  if (!action) return { kind: "skip_to", skipTo: "" };
  if ("skip_to" in action) return { kind: "skip_to", skipTo: action.skip_to };
  if ("end_and_submit" in action) return { kind: "end_and_submit", skipTo: "" };
  return { kind: "end_and_discard", skipTo: "" };
}

function conditionToDraft(
  condition: RuleCondition,
  siblings: QuestionContent[],
): ConditionDraft {
  const target = findSibling(siblings, condition.source_id);

  if (condition.family === "choice") {
    const marks: Record<string, ChoiceMark> = {};
    const optionIds = target?.family === "choice"
      ? target.definition.options.map((option) => option.id)
      : [
        ...(condition.requirements.required ?? []),
        ...(condition.requirements.forbidden ?? []),
        ...(condition.requirements.any_of ?? []),
      ];

    optionIds.forEach((optionId) => {
      marks[optionId] = "none";
    });
    (condition.requirements.required ?? []).forEach((optionId) => { marks[optionId] = "required"; });
    (condition.requirements.forbidden ?? []).forEach((optionId) => { marks[optionId] = "forbidden"; });
    (condition.requirements.any_of ?? []).forEach((optionId) => { marks[optionId] = "any_of"; });

    return { key: newConditionKey(), target_id: condition.source_id, family: "choice", marks };
  }

  if (condition.family === "matching") {
    const pairs: Record<string, string> = {};
    if (target?.family === "matching") {
      target.definition.prompts.forEach((prompt) => {
        pairs[prompt.id] = "";
      });
    }
    (condition.requirements.required ?? []).forEach((pair) => {
      Object.entries(pair).forEach(([promptId, matchId]) => {
        pairs[promptId] = matchId;
      });
    });
    return { key: newConditionKey(), target_id: condition.source_id, family: "matching", pairs };
  }

  if (condition.family === "rating") {
    return {
      key: newConditionKey(),
      target_id: condition.source_id,
      family: "rating",
      min: condition.requirements.min ?? null,
      max: condition.requirements.max ?? null,
    };
  }

  return {
    key: newConditionKey(),
    target_id: condition.source_id,
    family: "field",
    numberOperator: condition.requirements.type === "date" ? "EQ" : condition.requirements.operator,
    numberValue: condition.requirements.type === "date" ? "" : String(condition.requirements.value ?? ""),
    dateOperator: condition.requirements.type === "date" ? condition.requirements.operator : "before",
    dateValue: condition.requirements.type === "date" ? condition.requirements.value : "",
  };
}

const sectionClass = "border-t border-border pt-3 first:border-t-0 first:pt-0";
const emptyTextClass = "m-0 px-4 py-2 text-[0.88rem] text-muted-foreground";
const addBtnClass = "rounded-2xl min-h-11 mx-4 mb-3 mt-1.5";
const choiceTagClass =
  "inline-flex items-center rounded-full border border-border bg-muted px-1.5 py-0.5 text-[0.72rem] font-bold uppercase text-muted-foreground";
const pickerHeadClass = "flex items-baseline justify-between gap-2";
const pickerTitleClass = "text-[0.95rem] font-semibold text-foreground";
const pickerHintClass =
  "text-[0.78rem] uppercase tracking-[0.04em] text-muted-foreground";
const toggleRowClass =
  "inline-flex items-center gap-1.5 whitespace-nowrap text-[0.85rem] text-muted-foreground";

export const RulesQuestion = forwardRef<RulesQuestionHandle, RulesQuestionProps>(function RulesQuestion(
  { onDelete, title: _title, initialTag, initialContent, idError, isCollapsed, onExpand, onEditModeChange, onDataChange, previousSiblings = [], followingSiblings = [] },
  ref,
) {
  const siblings = [...previousSiblings, ...followingSiblings];
  const initialThenDo = doToState(initialContent?.then.do);
  const initialElseDo = doToState(initialContent?.else?.do);
  void _title;
  const [isEditMode, setIsEditMode] = useState(true);
  const [tagValue, setTagValue] = useState(initialContent?.id ?? initialTag ?? "r1");
  const [match, setMatch] = useState<RuleMatch>(initialContent?.if.match ?? "ALL");
  const [conditions, setConditions] = useState<ConditionDraft[]>(
    () => initialContent?.if.conditions.map((condition) => conditionToDraft(condition, siblings)) ?? [],
  );
  const [thenMode, setThenMode] = useState<ThenMode>(initialContent?.then.do ? "do" : "set");
  const [setEntries, setSetEntries] = useState<Array<RuleSetEntry & { key: string }>>(
    () => initialContent?.then.set?.map((entry) => ({ key: newSetEntryKey(), ...entry })) ?? [],
  );
  const [thenDoKind, setThenDoKind] = useState<DoKind>(initialThenDo.kind);
  const [thenSkipTo, setThenSkipTo] = useState(initialThenDo.skipTo);
  const [includeElse, setIncludeElse] = useState(Boolean(initialContent?.else?.do));
  const [elseDoKind, setElseDoKind] = useState<DoKind>(initialElseDo.kind);
  const [elseSkipTo, setElseSkipTo] = useState(initialElseDo.skipTo);

  const previousOptions = [
    { value: "", label: "Select a question…" },
    ...previousSiblings.map(questionOption),
  ];
  const followingOptions = [
    { value: "", label: "Select a question…" },
    ...followingSiblings.map(questionOption),
  ];
  const siblingSignature = JSON.stringify(siblings);

  function buildThen(): RuleContent["then"] {
    if (thenMode === "set") {
      const set = setEntries
        .filter((entry) => entry.target_id)
        .map(({ key: _key, ...rest }) => {
          void _key;
          const out: RuleSetEntry = { target_id: rest.target_id };
          if (rest.visible !== undefined) out.visible = rest.visible;
          if (rest.required !== undefined) out.required = rest.required;
          return out;
        });
      return set.length ? { set } : {};
    }
    return { do: buildDo(thenDoKind, thenSkipTo) };
  }

  function buildDo(kind: DoKind, skipTo: string): RuleDoAction {
    if (kind === "skip_to") return { skip_to: skipTo };
    if (kind === "end_and_submit") return { end_and_submit: true };
    return { end_and_discard: true };
  }

  const ruleContent: RuleContent = useMemo(() => ({
    id: tagValue,
    if: {
      match,
      conditions: conditions
        .map((draft) => draftToCondition(draft, findSibling(siblings, draft.target_id)))
        .filter((c): c is RuleCondition => c !== null),
    },
    then: buildThen(),
    ...(includeElse
      ? { else: { do: buildDo(elseDoKind, elseSkipTo) } }
      : {}),
  }), [
    tagValue,
    match,
    conditions,
    thenMode,
    setEntries,
    thenDoKind,
    thenSkipTo,
    includeElse,
    elseDoKind,
    elseSkipTo,
    siblingSignature,
  ]);

  useImperativeHandle(ref, () => ({
    getData() {
      return ruleContent;
    },
  }));

  useEffect(() => {
    onDataChange?.(ruleContent);
  }, [onDataChange, ruleContent]);

  function toggleEditMode() {
    setIsEditMode((current) => {
      const nextMode = !current;
      onEditModeChange?.(nextMode);
      return nextMode;
    });
  }

  function addCondition() {
    setConditions((current) => [
      ...current,
      { key: newConditionKey(), target_id: "", family: null },
    ]);
  }

  function removeCondition(key: string) {
    setConditions((current) => current.filter((c) => c.key !== key));
  }

  function retargetCondition(key: string, nextTargetId: string) {
    setConditions((current) =>
      current.map((draft) => {
        if (draft.key !== key) return draft;
        if (!nextTargetId) {
          return { key, target_id: "", family: null };
        }
        const target = findSibling(siblings, nextTargetId);
        if (!target) return draft;
        return buildConditionFromTarget(target, key);
      }),
    );
  }

  function updateChoiceMark(key: string, optionId: string, mark: ChoiceMark) {
    setConditions((current) =>
      current.map((draft) => {
        if (draft.key !== key || draft.family !== "choice") return draft;
        return { ...draft, marks: { ...draft.marks, [optionId]: mark } };
      }),
    );
  }

  function updateMatchingPair(key: string, promptId: string, matchId: string) {
    setConditions((current) =>
      current.map((draft) => {
        if (draft.key !== key || draft.family !== "matching") return draft;
        return { ...draft, pairs: { ...draft.pairs, [promptId]: matchId } };
      }),
    );
  }

  function updateRatingRange(key: string, field: "min" | "max", value: number | null) {
    setConditions((current) =>
      current.map((draft) => {
        if (draft.key !== key || draft.family !== "rating") return draft;
        return { ...draft, [field]: value } as ConditionDraft;
      }),
    );
  }

  function updateFieldCondition(
    key: string,
    patch: Partial<Extract<ConditionDraft, { family: "field" }>>,
  ) {
    setConditions((current) =>
      current.map((draft) => {
        if (draft.key !== key || draft.family !== "field") return draft;
        return { ...draft, ...patch };
      }),
    );
  }

  function addSetEntry() {
    setSetEntries((current) => [
      ...current,
      { key: newSetEntryKey(), target_id: "", visible: undefined, required: undefined },
    ]);
  }

  function updateSetEntry(key: string, patch: Partial<RuleSetEntry>) {
    setSetEntries((current) =>
      current.map((entry) => (entry.key === key ? { ...entry, ...patch } : entry)),
    );
  }

  function removeSetEntry(key: string) {
    setSetEntries((current) => current.filter((entry) => entry.key !== key));
  }

  function renderConditionBody(draft: ConditionDraft) {
    if (draft.family === null) {
      return (
        <p className="m-0 text-[0.88rem] text-muted-foreground">
          Choose a question to configure how its answer should match.
        </p>
      );
    }

    const target = findSibling(siblings, draft.target_id);
    if (!target) {
      return (
        <p className="m-0 text-[0.88rem] text-muted-foreground">
          The target question is no longer available.
        </p>
      );
    }

    if (draft.family === "choice") {
      return renderChoicePicker(draft.key, target as ChoiceContent, draft.marks);
    }
    if (draft.family === "matching") {
      return renderMatchingPicker(draft.key, target as MatchingContent, draft.pairs);
    }
    if (draft.family === "rating") {
      return renderRatingPicker(draft.key, target as RatingContent, draft.min, draft.max);
    }
    return renderFieldPicker(draft, target as FieldContent);
  }

  function renderChoicePicker(
    key: string,
    target: ChoiceContent,
    marks: Record<string, ChoiceMark>,
  ) {
    return (
      <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
        <div className={pickerHeadClass}>
          <span className={pickerTitleClass}>{target.title || target.label || target.id}</span>
          <span className={pickerHintClass}>Mark each choice</span>
        </div>
        <div className="flex flex-col gap-1.5">
          {target.definition.options.map((option) => {
            const mark = marks[option.id] ?? "none";
            const activeRow = CHOICE_MARK_OPTIONS.find((o) => o.value === mark)?.rowActive ?? "";
            return (
              <div
                key={option.id}
                className={`flex items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2 px-2.5 transition-colors ${activeRow}`}
              >
                <span className="flex min-w-0 flex-1 items-center gap-2">
                  <span className={choiceTagClass}>{option.id}</span>
                  <span className="overflow-hidden text-ellipsis text-[0.92rem] text-foreground">
                    {option.label || "—"}
                  </span>
                </span>
                <div className="flex flex-wrap gap-1" role="radiogroup" aria-label="Requirement">
                  {CHOICE_MARK_OPTIONS.map((opt) => {
                    const active = mark === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        role="radio"
                        aria-checked={active}
                        className={`rounded-full border px-2.5 py-1 text-[0.78rem] font-semibold transition-colors disabled:cursor-default disabled:opacity-60 ${
                          active
                            ? opt.btnActive
                            : "border-border bg-card text-muted-foreground hover:bg-muted"
                        }`}
                        disabled={!isEditMode}
                        onClick={() => updateChoiceMark(key, option.id, opt.value)}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    );
  }

  function renderMatchingPicker(
    key: string,
    target: MatchingContent,
    pairs: Record<string, string>,
  ) {
    const matchOptions = [
      { value: "", label: "Any match" },
      ...target.definition.matches.map((m) => ({
        value: m.id,
        label: `${m.label || "—"} (${m.id})`,
      })),
    ];
    return (
      <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
        <div className={pickerHeadClass}>
          <span className={pickerTitleClass}>{target.title || target.label || target.id}</span>
          <span className={pickerHintClass}>Required pairings</span>
        </div>
        <div className="flex flex-col gap-2">
          {target.definition.prompts.map((prompt) => (
            <div key={prompt.id} className="grid grid-cols-1 items-center gap-3 sm:grid-cols-2">
              <span className="flex min-w-0 flex-1 items-center gap-2">
                <span className={choiceTagClass}>{prompt.id}</span>
                <span className="overflow-hidden text-ellipsis text-[0.92rem] text-foreground">
                  {prompt.label || "—"}
                </span>
              </span>
              <Select
                value={pairs[prompt.id] ?? ""}
                options={matchOptions}
                disabled={!isEditMode}
                onChange={(event) => updateMatchingPair(key, prompt.id, event.target.value)}
              />
            </div>
          ))}
        </div>
      </Card>
    );
  }

  function renderRatingPicker(
    key: string,
    target: RatingContent,
    min: number | null,
    max: number | null,
  ) {
    const def = target.definition;
    const bounds =
      def.variant === "slider"
        ? { low: def.range.min, high: def.range.max }
        : def.variant === "star"
          ? { low: 0, high: def.stars }
          : { low: 1, high: 5 };
    return (
      <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
        <div className={pickerHeadClass}>
          <span className={pickerTitleClass}>{target.title || target.label || target.id}</span>
          <span className={pickerHintClass}>
            Range {bounds.low} to {bounds.high}
          </span>
        </div>
        <div className="flex flex-wrap gap-4">
          <label className="flex flex-col gap-1.5 text-[0.82rem] text-muted-foreground">
            <span>Min</span>
            <NumberStepper
              ariaLabel="Minimum value"
              size="sm"
              value={min ?? bounds.low}
              min={bounds.low}
              max={bounds.high}
              disabled={!isEditMode}
              onChange={(value) => updateRatingRange(key, "min", value)}
            />
          </label>
          <label className="flex flex-col gap-1.5 text-[0.82rem] text-muted-foreground">
            <span>Max</span>
            <NumberStepper
              ariaLabel="Maximum value"
              size="sm"
              value={max ?? bounds.high}
              min={bounds.low}
              max={bounds.high}
              disabled={!isEditMode}
              onChange={(value) => updateRatingRange(key, "max", value)}
            />
          </label>
        </div>
      </Card>
    );
  }

  function renderFieldPicker(
    draft: Extract<ConditionDraft, { family: "field" }>,
    target: FieldContent,
  ) {
    const isDate = target.definition.field_type === "date";
    return (
      <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
        <div className={pickerHeadClass}>
          <span className={pickerTitleClass}>{target.title || target.label || target.id}</span>
          <span className={pickerHintClass}>{target.definition.field_type}</span>
        </div>
        <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[auto_1fr]">
          {isDate ? (
            <>
              <Select
                label="Operator"
                value={draft.dateOperator}
                options={DATE_OP_OPTIONS}
                disabled={!isEditMode}
                onChange={(event) =>
                  updateFieldCondition(draft.key, {
                    dateOperator: event.target.value as FieldDateOperator,
                  })
                }
              />
              <Input
                label="Date"
                type="date"
                value={draft.dateValue}
                disabled={!isEditMode}
                onChange={(event) =>
                  updateFieldCondition(draft.key, { dateValue: event.target.value })
                }
              />
            </>
          ) : (
            <>
              <Select
                label="Operator"
                value={draft.numberOperator}
                options={NUMBER_OP_OPTIONS}
                disabled={!isEditMode}
                onChange={(event) =>
                  updateFieldCondition(draft.key, {
                    numberOperator: event.target.value as FieldNumberOperator,
                  })
                }
              />
              <Input
                label="Value"
                type={target.definition.field_type === "number" ? "number" : "text"}
                value={draft.numberValue}
                disabled={!isEditMode}
                onChange={(event) =>
                  updateFieldCondition(draft.key, { numberValue: event.target.value })
                }
              />
            </>
          )}
        </div>
      </Card>
    );
  }

  function renderDoEditor(
    kind: DoKind,
    skipTo: string,
    onKindChange: (kind: DoKind) => void,
    onSkipToChange: (value: string) => void,
  ) {
    const skipOptions = followingOptions;
    return (
      <div className="flex flex-row flex-wrap items-end gap-3 px-4 py-3">
        <Select
          label="Action"
          value={kind}
          options={DO_OPTIONS}
          disabled={!isEditMode}
          onChange={(event) => onKindChange(event.target.value as DoKind)}
        />
        {kind === "skip_to" && (
          <Select
            label="Skip target"
            value={skipTo}
            options={skipOptions}
            disabled={!isEditMode}
            onChange={(event) => onSkipToChange(event.target.value)}
          />
        )}
      </div>
    );
  }

  if (isCollapsed) {
    return <NodePillCollapsed family="Rule" tagValue={tagValue} title={tagValue} onExpand={() => { onExpand?.(); setIsEditMode(true); onEditModeChange?.(true); }} />;
  }

  return (
    <section className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""}`} aria-label="Rules question">
      <NodePillTopbar
        family="Rule"
        tagValue={tagValue}
        onTagChange={setTagValue}
        idError={idError}
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
      />

      <div className={nodePillBodyClass}>
        <div className={`${nodePillFieldClass} ${sectionClass}`}>
          <NodePillFieldHead label="If">
            {isEditMode && (
              <Select
                value={match}
                options={MATCH_OPTIONS}
                onChange={(event) => setMatch(event.target.value as RuleMatch)}
              />
            )}
          </NodePillFieldHead>

          <div className="flex flex-col gap-3 px-4 py-3">
            {conditions.length === 0 && <p className={emptyTextClass}>No conditions yet.</p>}
            {conditions.map((draft, index) => (
              <Card key={draft.key} tone="muted" size="sm" className="flex flex-col gap-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[0.78rem] font-bold uppercase tracking-[0.04em] text-muted-foreground">
                    Condition {index + 1}
                  </span>
                  {isEditMode && (
                    <Button
                      type="button"
                      variant="danger"
                      size="xs"
                      pill
                      onClick={() => removeCondition(draft.key)}
                    >
                      Remove
                    </Button>
                  )}
                </div>
                <Select
                  label="Question"
                  value={draft.target_id}
                  options={previousOptions}
                  disabled={!isEditMode}
                  onChange={(event) => retargetCondition(draft.key, event.target.value)}
                />
                {renderConditionBody(draft)}
              </Card>
            ))}
            {isEditMode && (
              <Button
                className={addBtnClass}
                type="button"
                variant="ghost"
                borderStyle="dotted"
                onClick={addCondition}
              >
                <span aria-hidden="true">+</span> Add condition
              </Button>
            )}
          </div>
        </div>

        <div className={`${nodePillFieldClass} ${sectionClass}`}>
          <NodePillFieldHead label="Then">
            {isEditMode && (
              <Select
                value={thenMode}
                options={[
                  { value: "set", label: "Set" },
                  { value: "do", label: "Do" },
                ]}
                onChange={(event) => setThenMode(event.target.value as ThenMode)}
              />
            )}
          </NodePillFieldHead>

          {thenMode === "set" ? (
            <CardStack gap="sm" className="px-4 py-3">
              {setEntries.length === 0 && <p className={emptyTextClass}>No set entries yet.</p>}
              {setEntries.map((entry) => (
                <Card key={entry.key} tone="muted" size="sm" className="grid grid-cols-1 items-center gap-2.5 sm:grid-cols-[1fr_auto_auto_auto]">
                  <Select
                    label="Target"
                    value={entry.target_id}
                    options={followingOptions}
                    disabled={!isEditMode}
                    onChange={(event) =>
                      updateSetEntry(entry.key, { target_id: event.target.value })
                    }
                  />
                  <label className={toggleRowClass}>
                    <input
                      type="checkbox"
                      checked={entry.visible === false}
                      disabled={!isEditMode}
                      onChange={(event) =>
                        updateSetEntry(entry.key, {
                          visible: event.target.checked ? false : undefined,
                        })
                      }
                    />
                    Hide
                  </label>
                  <label className={toggleRowClass}>
                    <input
                      type="checkbox"
                      checked={entry.required === true}
                      disabled={!isEditMode}
                      onChange={(event) =>
                        updateSetEntry(entry.key, {
                          required: event.target.checked ? true : undefined,
                        })
                      }
                    />
                    Required
                  </label>
                  {isEditMode && (
                    <Button
                      type="button"
                      variant="danger"
                      size="xs"
                      pill
                      onClick={() => removeSetEntry(entry.key)}
                    >
                      Remove
                    </Button>
                  )}
                </Card>
              ))}
              {isEditMode && (
                <Button
                  className={addBtnClass}
                  type="button"
                  variant="ghost"
                  borderStyle="dotted"
                  onClick={addSetEntry}
                >
                  <span aria-hidden="true">+</span> Add set
                </Button>
              )}
            </CardStack>
          ) : (
            renderDoEditor(thenDoKind, thenSkipTo, setThenDoKind, setThenSkipTo)
          )}
        </div>

        <div className={`${nodePillFieldClass} ${sectionClass}`}>
          <NodePillFieldHead label="Else">
            {isEditMode && (
              <label className={toggleRowClass}>
                <input
                  type="checkbox"
                  checked={includeElse}
                  onChange={(event) => setIncludeElse(event.target.checked)}
                />
                Enabled
              </label>
            )}
          </NodePillFieldHead>

          {includeElse ? (
            renderDoEditor(elseDoKind, elseSkipTo, setElseDoKind, setElseSkipTo)
          ) : (
            <p className={emptyTextClass}>No else branch.</p>
          )}
        </div>
      </div>
    </section>
  );
});
