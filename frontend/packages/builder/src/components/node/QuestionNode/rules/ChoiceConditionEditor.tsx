import { Card } from "@flowform/ui";
import type { ChoiceContent, RuleCondition } from "../../questionTypes";
import {
  CHOICE_MARK_OPTIONS,
  choiceTagClass,
  getChoiceMark,
  pickerHeadClass,
  pickerHintClass,
  pickerTitleClass,
  setChoiceMark,
  type ChoiceMark,
} from "./ruleEditorHelpers";

type ChoiceCondition = Extract<RuleCondition, { family: "choice" }>;

interface ChoiceConditionEditorProps {
  condition: ChoiceCondition;
  target: ChoiceContent;
  targetTitle: string;
  isEditMode: boolean;
  onChange: (next: ChoiceCondition) => void;
}

export function ChoiceConditionEditor({
  condition,
  target,
  targetTitle,
  isEditMode,
  onChange,
}: ChoiceConditionEditorProps) {
  function setMark(optionId: string, mark: ChoiceMark) {
    onChange({
      ...condition,
      requirements: setChoiceMark(condition.requirements, optionId, mark),
    });
  }

  return (
    <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
      <div className={pickerHeadClass}>
        <span className={pickerTitleClass}>{targetTitle}</span>
        <span className={pickerHintClass}>Mark each choice</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {target.definition.options.map((option) => {
          const mark = getChoiceMark(condition.requirements, option.id);
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
                      onClick={() => setMark(option.id, opt.value)}
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
