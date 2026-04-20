import { useEffect, useState, forwardRef, useImperativeHandle } from "react";
import "./RulesQuestion.css";
import { NodePillTopbar, NodePillFieldHead } from "./NodePillShell";
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

const CHOICE_MARK_OPTIONS: Array<{ value: ChoiceMark; label: string; className: string }> = [
  { value: "none", label: "Ignore", className: "rules-question__mark--none" },
  { value: "required", label: "Required", className: "rules-question__mark--required" },
  { value: "forbidden", label: "Forbidden", className: "rules-question__mark--forbidden" },
  { value: "any_of", label: "Any of", className: "rules-question__mark--any_of" },
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
    return { target_id: draft.target_id, family: "choice", requirements: reqs };
  }

  if (draft.family === "matching") {
    const required: Array<Record<string, string>> = [];
    Object.entries(draft.pairs).forEach(([promptId, matchId]) => {
      if (matchId) required.push({ [promptId]: matchId });
    });
    const reqs: MatchingRequirements = required.length ? { required } : {};
    return { target_id: draft.target_id, family: "matching", requirements: reqs };
  }

  if (draft.family === "rating") {
    const reqs: RatingRequirements = {};
    if (draft.min !== null) reqs.min = draft.min;
    if (draft.max !== null) reqs.max = draft.max;
    return { target_id: draft.target_id, family: "rating", requirements: reqs };
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
  return { target_id: draft.target_id, family: "field", requirements };
}

function findSibling(siblings: QuestionContent[], id: string) {
  return siblings.find((s) => s.id === id);
}

export const RulesQuestion = forwardRef<RulesQuestionHandle, RulesQuestionProps>(function RulesQuestion(
  { onDelete, title: _title, onEditModeChange, onDataChange, previousSiblings = [], followingSiblings = [] },
  ref,
) {
  const siblings = [...previousSiblings, ...followingSiblings];
  void _title;
  const [isEditMode, setIsEditMode] = useState(true);
  const [tagValue, setTagValue] = useState("r1");
  const [match, setMatch] = useState<RuleMatch>("ALL");
  const [conditions, setConditions] = useState<ConditionDraft[]>([]);
  const [thenMode, setThenMode] = useState<ThenMode>("set");
  const [setEntries, setSetEntries] = useState<Array<RuleSetEntry & { key: string }>>([]);
  const [thenDoKind, setThenDoKind] = useState<DoKind>("skip_to");
  const [thenSkipTo, setThenSkipTo] = useState("");
  const [includeElse, setIncludeElse] = useState(false);
  const [elseDoKind, setElseDoKind] = useState<DoKind>("skip_to");
  const [elseSkipTo, setElseSkipTo] = useState("");

  const previousOptions = [
    { value: "", label: "Select a question…" },
    ...previousSiblings.map(questionOption),
  ];
  const followingOptions = [
    { value: "", label: "Select a question…" },
    ...followingSiblings.map(questionOption),
  ];

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

  const ruleContent: RuleContent = {
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
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return ruleContent;
    },
  }));

  useEffect(() => {
    onDataChange?.(ruleContent);
  }, [
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
    siblings,
  ]);

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
        <p className="rules-question__condition-empty">
          Choose a question to configure how its answer should match.
        </p>
      );
    }

    const target = findSibling(siblings, draft.target_id);
    if (!target) {
      return (
        <p className="rules-question__condition-empty">
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
      <div className="rules-question__picker rules-question__picker--choice">
        <div className="rules-question__picker-head">
          <span className="rules-question__picker-title">{target.title || target.label || target.id}</span>
          <span className="rules-question__picker-hint">Mark each choice</span>
        </div>
        <div className="rules-question__choice-list">
          {target.definition.options.map((option) => {
            const mark = marks[option.id] ?? "none";
            return (
              <div
                key={option.id}
                className={`rules-question__choice-row rules-question__mark--${mark}`}
              >
                <span className="rules-question__choice-label">
                  <span className="rules-question__choice-tag">{option.id}</span>
                  <span className="rules-question__choice-text">{option.label || "—"}</span>
                </span>
                <div className="rules-question__mark-group" role="radiogroup" aria-label="Requirement">
                  {CHOICE_MARK_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      role="radio"
                      aria-checked={mark === opt.value}
                      className={`rules-question__mark-btn ${opt.className} ${
                        mark === opt.value ? "rules-question__mark-btn--active" : ""
                      }`}
                      disabled={!isEditMode}
                      onClick={() => updateChoiceMark(key, option.id, opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
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
      <div className="rules-question__picker">
        <div className="rules-question__picker-head">
          <span className="rules-question__picker-title">{target.title || target.label || target.id}</span>
          <span className="rules-question__picker-hint">Required pairings</span>
        </div>
        <div className="rules-question__matching-list">
          {target.definition.prompts.map((prompt) => (
            <div key={prompt.id} className="rules-question__matching-row">
              <span className="rules-question__matching-prompt">
                <span className="rules-question__choice-tag">{prompt.id}</span>
                <span className="rules-question__choice-text">{prompt.label || "—"}</span>
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
      </div>
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
      <div className="rules-question__picker">
        <div className="rules-question__picker-head">
          <span className="rules-question__picker-title">{target.title || target.label || target.id}</span>
          <span className="rules-question__picker-hint">
            Range {bounds.low} to {bounds.high}
          </span>
        </div>
        <div className="rules-question__rating-row">
          <label className="rules-question__rating-field">
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
          <label className="rules-question__rating-field">
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
      </div>
    );
  }

  function renderFieldPicker(
    draft: Extract<ConditionDraft, { family: "field" }>,
    target: FieldContent,
  ) {
    const isDate = target.definition.field_type === "date";
    return (
      <div className="rules-question__picker">
        <div className="rules-question__picker-head">
          <span className="rules-question__picker-title">{target.title || target.label || target.id}</span>
          <span className="rules-question__picker-hint">{target.definition.field_type}</span>
        </div>
        <div className="rules-question__field-row">
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
      </div>
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
      <div className="rules-question__do-row">
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

  return (
    <section className={`node-pill rules-question ${isEditMode ? "node-pill--edit" : ""}`} aria-label="Rules question">
      <NodePillTopbar
        family="Rule"
        tagValue={tagValue}
        onTagChange={setTagValue}
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
      />

      <div className="node-pill__body">
        {/* If section */}
        <div className="node-pill__field rules-question__section rules-question__section--if">
          <NodePillFieldHead label="If">
            {isEditMode && (
              <Select
                value={match}
                options={MATCH_OPTIONS}
                onChange={(event) => setMatch(event.target.value as RuleMatch)}
              />
            )}
          </NodePillFieldHead>

          <div className="rules-question__conditions">
            {conditions.length === 0 && (
              <p className="rules-question__empty">No conditions yet.</p>
            )}
            {conditions.map((draft, index) => (
              <div key={draft.key} className="rules-question__condition">
                <div className="rules-question__condition-head">
                  <span className="rules-question__condition-label">Condition {index + 1}</span>
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
              </div>
            ))}
            {isEditMode && (
              <Button
                className="rules-question__add"
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

        {/* Then section */}
        <div className="node-pill__field rules-question__section rules-question__section--then">
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
            <div className="rules-question__set-list">
              {setEntries.length === 0 && (
                <p className="rules-question__empty">No set entries yet.</p>
              )}
              {setEntries.map((entry) => (
                <div key={entry.key} className="rules-question__set-row">
                  <Select
                    label="Target"
                    value={entry.target_id}
                    options={followingOptions}
                    disabled={!isEditMode}
                    onChange={(event) =>
                      updateSetEntry(entry.key, { target_id: event.target.value })
                    }
                  />
                  <label className="rules-question__set-toggle">
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
                  <label className="rules-question__set-toggle">
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
                </div>
              ))}
              {isEditMode && (
                <Button
                  className="rules-question__add"
                  type="button"
                  variant="ghost"
                  borderStyle="dotted"
                  onClick={addSetEntry}
                >
                  <span aria-hidden="true">+</span> Add set
                </Button>
              )}
            </div>
          ) : (
            renderDoEditor(thenDoKind, thenSkipTo, setThenDoKind, setThenSkipTo)
          )}
        </div>

        {/* Else section */}
        <div className="node-pill__field rules-question__section rules-question__section--else">
          <NodePillFieldHead label="Else">
            {isEditMode && (
              <label className="rules-question__else-toggle">
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
            <p className="rules-question__empty">No else branch.</p>
          )}
        </div>
      </div>
    </section>
  );
});
