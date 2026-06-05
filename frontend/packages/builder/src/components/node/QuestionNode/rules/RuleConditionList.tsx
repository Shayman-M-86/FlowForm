import { Button, Card, Select } from "@flowform/ui";
import { NodePillFieldHead } from "../../NodePillShell";
import { nodePillFieldClass } from "../../nodePillStyles";
import type { RuleCondition, RuleMatch } from "../../questionTypes";
import { RuleConditionEditor } from "./RuleConditionEditor";
import {
  addBtnClass,
  createDefaultCondition,
  emptyTextClass,
  findSibling,
  MATCH_OPTIONS,
  questionOption,
  sectionClass,
  type QuestionNode,
} from "./ruleEditorHelpers";

interface RuleConditionListProps {
  match: RuleMatch;
  conditions: RuleCondition[];
  siblings: QuestionNode[];
  isEditMode: boolean;
  onMatchChange: (match: RuleMatch) => void;
  onConditionsChange: (conditions: RuleCondition[]) => void;
}

export function RuleConditionList({
  match,
  conditions,
  siblings,
  isEditMode,
  onMatchChange,
  onConditionsChange,
}: RuleConditionListProps) {
  const questionOptions = [
    { value: "", label: "Select a question…" },
    ...siblings.map(questionOption),
  ];

  function replaceCondition(index: number, next: RuleCondition) {
    onConditionsChange(conditions.map((c, i) => (i === index ? next : c)));
  }

  function removeCondition(index: number) {
    onConditionsChange(conditions.filter((_, i) => i !== index));
  }

  function retargetCondition(index: number, targetId: string) {
    const target = findSibling(siblings, targetId);
    if (!target) return;
    replaceCondition(index, createDefaultCondition(target));
  }

  function addCondition(targetId: string) {
    const target = findSibling(siblings, targetId);
    if (!target) return;
    onConditionsChange([...conditions, createDefaultCondition(target)]);
  }

  return (
    <div className={`${nodePillFieldClass} ${sectionClass}`}>
      <NodePillFieldHead label="If">
        {isEditMode && (
          <Select
            value={match}
            options={MATCH_OPTIONS}
            onChange={(event) => onMatchChange(event.target.value as RuleMatch)}
          />
        )}
      </NodePillFieldHead>

      <div className="flex flex-col gap-3 px-4 py-3">
        {conditions.length === 0 && <p className={emptyTextClass}>No conditions yet.</p>}
        {conditions.map((condition, index) => (
          <Card key={index} tone="muted" size="sm" className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[0.78rem] font-bold uppercase tracking-[0.04em] text-muted-foreground">
                Condition {index + 1}
              </span>
              {isEditMode && (
                <Button
                  type="button"
                  variant="danger"
                  size="xs"
                  onClick={() => removeCondition(index)}
                >
                  Remove
                </Button>
              )}
            </div>
            <Select
              label="Question"
              value={condition.target_id}
              options={questionOptions}
              disabled={!isEditMode}
              onChange={(event) => retargetCondition(index, event.target.value)}
            />
            <RuleConditionEditor
              condition={condition}
              siblings={siblings}
              isEditMode={isEditMode}
              onChange={(next) => replaceCondition(index, next)}
            />
          </Card>
        ))}
        {isEditMode && (
          <Select
            className={addBtnClass}
            label="Add condition"
            value=""
            options={questionOptions}
            onChange={(event) => {
              if (event.target.value) addCondition(event.target.value);
            }}
          />
        )}
      </div>
    </div>
  );
}
