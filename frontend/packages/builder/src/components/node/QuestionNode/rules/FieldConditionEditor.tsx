import { useEffect, useState } from "react";
import { Card, Input, Select } from "@flowform/ui";
import type {
  FieldContent,
  FieldDateOperator,
  FieldNumberOperator,
  RuleCondition,
} from "../../questionTypes";
import {
  DATE_OP_OPTIONS,
  NUMBER_OP_OPTIONS,
  pickerHeadClass,
  pickerHintClass,
  pickerTitleClass,
} from "./ruleEditorHelpers";

type FieldCondition = Extract<RuleCondition, { family: "field" }>;

interface FieldConditionEditorProps {
  condition: FieldCondition;
  target: FieldContent;
  targetTitle: string;
  isEditMode: boolean;
  onChange: (next: FieldCondition) => void;
}

export function FieldConditionEditor({
  condition,
  target,
  targetTitle,
  isEditMode,
  onChange,
}: FieldConditionEditorProps) {
  const requirements = condition.requirements;
  const isDate = requirements.type === "date";

  // Temporary string for the number input so partial values ("", "-", "1.")
  // are typeable; the canonical value stays a number on the generated condition.
  const [numberDraft, setNumberDraft] = useState(
    requirements.type === "number" ? String(requirements.value) : "",
  );

  useEffect(() => {
    if (requirements.type === "number") {
      setNumberDraft(String(requirements.value));
    }
  }, [condition.target_id, requirements.type]); // re-sync when target/family changes

  function updateRequirements(next: FieldCondition["requirements"]) {
    onChange({ ...condition, requirements: next });
  }

  return (
    <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
      <div className={pickerHeadClass}>
        <span className={pickerTitleClass}>{targetTitle}</span>
        <span className={pickerHintClass}>{target.definition.field_type}</span>
      </div>
      <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[auto_1fr]">
        {isDate ? (
          <>
            <Select
              label="Operator"
              value={requirements.operator}
              options={DATE_OP_OPTIONS}
              disabled={!isEditMode}
              onChange={(event) =>
                updateRequirements({
                  type: "date",
                  operator: event.target.value as FieldDateOperator,
                  value: requirements.type === "date" ? requirements.value : "",
                })
              }
            />
            <Input
              label="Date"
              type="date"
              value={requirements.type === "date" ? requirements.value : ""}
              disabled={!isEditMode}
              onChange={(event) =>
                updateRequirements({
                  type: "date",
                  operator: requirements.operator as FieldDateOperator,
                  value: event.target.value,
                })
              }
            />
          </>
        ) : (
          <>
            <Select
              label="Operator"
              value={requirements.operator}
              options={NUMBER_OP_OPTIONS}
              disabled={!isEditMode}
              onChange={(event) =>
                updateRequirements({
                  type: "number",
                  operator: event.target.value as FieldNumberOperator,
                  value: requirements.type === "number" ? requirements.value : 0,
                })
              }
            />
            <Input
              label="Value"
              type={target.definition.field_type === "number" ? "number" : "text"}
              value={numberDraft}
              disabled={!isEditMode}
              onChange={(event) => {
                const nextDraft = event.target.value;
                setNumberDraft(nextDraft);
                updateRequirements({
                  type: "number",
                  operator: requirements.operator as FieldNumberOperator,
                  value: nextDraft.trim() === "" ? 0 : Number(nextDraft) || 0,
                });
              }}
            />
          </>
        )}
      </div>
    </Card>
  );
}
