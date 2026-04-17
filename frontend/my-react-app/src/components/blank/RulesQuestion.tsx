import { useEffect, useState, forwardRef, useImperativeHandle } from "react";
import "./RulesQuestion.css";
import { blurOnEnter } from "./blankPillUtils";
import { BlankPillTopbar, BlankPillCharCount, BlankPillFieldHead } from "./BlankPillShell";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Button } from "../ui/Button";

type Operator = "equals" | "not_equals" | "greater_than" | "less_than" | "contains" | "is_empty";
type Action = "skip_to" | "show" | "hide" | "require";

interface Rule {
  id: string;
  sourceField: string;
  operator: Operator;
  value: string;
  action: Action;
  targetField: string;
}

interface RulesQuestionData {
  id: string;
  title: string;
  family: "rules";
  rules: {
    items: Array<{
      source_field: string;
      operator: Operator;
      value: string;
      action: Action;
      target_field: string;
    }>;
  };
}

export type { RulesQuestionData };

export interface RulesQuestionHandle {
  getData(): RulesQuestionData;
}

interface RulesQuestionProps {
  onDelete?: () => void;
  title?: string;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (summary: { title: string; id: string }) => void;
}

const OPERATOR_OPTIONS: Array<{ value: Operator; label: string }> = [
  { value: "equals", label: "Equals" },
  { value: "not_equals", label: "Does not equal" },
  { value: "greater_than", label: "Greater than" },
  { value: "less_than", label: "Less than" },
  { value: "contains", label: "Contains" },
  { value: "is_empty", label: "Is empty" },
];

const ACTION_OPTIONS: Array<{ value: Action; label: string }> = [
  { value: "skip_to", label: "Skip to" },
  { value: "show", label: "Show" },
  { value: "hide", label: "Hide" },
  { value: "require", label: "Require" },
];

function operatorLabel(operator: Operator): string {
  return OPERATOR_OPTIONS.find((o) => o.value === operator)?.label ?? operator;
}

function actionLabel(action: Action): string {
  return ACTION_OPTIONS.find((a) => a.value === action)?.label ?? action;
}

let ruleCounter = 0;
function nextRuleId(): string {
  ruleCounter += 1;
  return `rule_${ruleCounter}`;
}

function createEmptyRule(): Rule {
  return {
    id: nextRuleId(),
    sourceField: "",
    operator: "equals",
    value: "",
    action: "skip_to",
    targetField: "",
  };
}

export const RulesQuestion = forwardRef<RulesQuestionHandle, RulesQuestionProps>(function RulesQuestion({ onDelete, title, onEditModeChange, onDataChange }, ref) {
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(title ?? "");
  const [tagValue, setTagValue] = useState("question_id_1");
  const [rules, setRules] = useState<Rule[]>(() => [createEmptyRule()]);

  const rulesQuestionData: RulesQuestionData = {
    id: tagValue,
    title: titleValue,
    family: "rules",
    rules: {
      items: rules.map((rule) => ({
        source_field: rule.sourceField,
        operator: rule.operator,
        value: rule.value,
        action: rule.action,
        target_field: rule.targetField,
      })),
    },
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return rulesQuestionData;
    },
  }));

  useEffect(() => {
    onDataChange?.({ title: titleValue, id: tagValue });
  }, [titleValue, tagValue]);

  function updateRule(ruleId: string, patch: Partial<Omit<Rule, "id">>) {
    setRules((current) =>
      current.map((rule) => (rule.id === ruleId ? { ...rule, ...patch } : rule)),
    );
  }

  function removeRule(ruleId: string) {
    setRules((current) => {
      if (current.length <= 1) return current;
      return current.filter((rule) => rule.id !== ruleId);
    });
  }

  function addRule() {
    setRules((current) => [...current, createEmptyRule()]);
  }

  function toggleEditMode() {
    setIsEditMode((current) => {
      const nextMode = !current;
      onEditModeChange?.(nextMode);
      return nextMode;
    });
  }

  const filledRules = rules.filter((rule) => rule.sourceField.trim() || rule.targetField.trim());

  return (
    <section className={`blank-pill rules-question ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Rules question">
      <BlankPillTopbar
        family="Rules"
        tagValue={tagValue}
        onTagChange={setTagValue}
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
      />

      <div className="blank-pill__body">
        <div className="blank-pill__field">
          <BlankPillFieldHead label="Rules">
            {isEditMode && (
              <BlankPillCharCount
                label="Count"
                value={rules.length}
              />
            )}
          </BlankPillFieldHead>

          <div className="rules-question__panel">
            {isEditMode && (
              <>
                <div className="rules-question__rules">
                  {rules.map((rule, index) => (
                    <div key={rule.id} className="rules-question__rule rules-question__rule--edit">
                      <div className="rules-question__rule-header">
                        <span className="rules-question__rule-number">Rule {index + 1}</span>
                        {rules.length > 1 && (
                          <Button
                            type="button"
                            variant="danger"
                            size="xs"
                            pill
                            onClick={() => removeRule(rule.id)}
                          >
                            Remove
                          </Button>
                        )}
                      </div>

                      <div className="rules-question__rule-fields">
                        <Input
                          label="If field"
                          type="text"
                          placeholder="source_field_id"
                          value={rule.sourceField}
                          maxLength={40}
                          onChange={(event) => updateRule(rule.id, { sourceField: event.target.value })}
                          onKeyDown={blurOnEnter}
                        />
                        <span className="rules-question__rule-keyword">is</span>
                        <Select
                          label="Operator"
                          value={rule.operator}
                          options={OPERATOR_OPTIONS}
                          onChange={(event) => updateRule(rule.id, { operator: event.target.value as Operator })}
                        />
                      </div>

                      {rule.operator !== "is_empty" && (
                        <Input
                          label="Value"
                          type="text"
                          placeholder="Expected value"
                          value={rule.value}
                          maxLength={200}
                          onChange={(event) => updateRule(rule.id, { value: event.target.value })}
                          onKeyDown={blurOnEnter}
                        />
                      )}

                      <div className="rules-question__rule-action">
                        <Select
                          label="Then"
                          value={rule.action}
                          options={ACTION_OPTIONS}
                          onChange={(event) => updateRule(rule.id, { action: event.target.value as Action })}
                        />
                        <Input
                          label="Target field"
                          type="text"
                          placeholder="target_field_id"
                          value={rule.targetField}
                          maxLength={40}
                          onChange={(event) => updateRule(rule.id, { targetField: event.target.value })}
                          onKeyDown={blurOnEnter}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <Button
                  className="rules-question__add-rule"
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={addRule}
                >
                  <span aria-hidden="true">+</span> Add rule
                </Button>
              </>
            )}

            <div className="rules-question__preview">
              <span className="rules-question__preview-title">Preview</span>
              {filledRules.length === 0 ? (
                <span className="rules-question__preview-empty">No rules defined yet.</span>
              ) : (
                <div className="rules-question__preview-list">
                  {filledRules.map((rule, index) => (
                    <div key={rule.id} className="rules-question__preview-rule">
                      <div className="rules-question__preview-condition">
                        <span className="rules-question__preview-keyword">If</span>
                        <span className="rules-question__preview-value">{rule.sourceField || "?"}</span>
                        <span>{operatorLabel(rule.operator).toLowerCase()}</span>
                        {rule.operator !== "is_empty" && (
                          <span className="rules-question__preview-value">{rule.value || "?"}</span>
                        )}
                      </div>
                      <div className="rules-question__preview-action">
                        <span className="rules-question__preview-keyword">Then</span>{" "}
                        {actionLabel(rule.action).toLowerCase()}{" "}
                        <span className="rules-question__preview-value">{rule.targetField || "?"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="rules-question__preview-meta">
                <span>{rules.length} rule{rules.length !== 1 ? "s" : ""}</span>
                <span>{filledRules.length} configured</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
});
