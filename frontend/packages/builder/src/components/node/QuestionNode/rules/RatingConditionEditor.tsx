import { Card, NumberStepper } from "@flowform/ui";
import type { RatingContent, RuleCondition } from "../../questionTypes";
import {
  pickerHeadClass,
  pickerHintClass,
  pickerTitleClass,
} from "./ruleEditorHelpers";

type RatingCondition = Extract<RuleCondition, { family: "rating" }>;

interface RatingConditionEditorProps {
  condition: RatingCondition;
  target: RatingContent;
  targetTitle: string;
  isEditMode: boolean;
  onChange: (next: RatingCondition) => void;
}

export function RatingConditionEditor({
  condition,
  target,
  targetTitle,
  isEditMode,
  onChange,
}: RatingConditionEditorProps) {
  const def = target.definition;
  const bounds =
    def.variant === "slider"
      ? { low: def.range.min, high: def.range.max }
      : def.variant === "stars"
        ? { low: 0, high: def.stars }
        : { low: 1, high: 5 };

  const min = condition.requirements.min ?? null;
  const max = condition.requirements.max ?? null;

  function setRange(field: "min" | "max", value: number) {
    onChange({
      ...condition,
      requirements: { ...condition.requirements, [field]: value },
    });
  }

  return (
    <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
      <div className={pickerHeadClass}>
        <span className={pickerTitleClass}>{targetTitle}</span>
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
            onChange={(value) => setRange("min", value)}
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
            onChange={(value) => setRange("max", value)}
          />
        </label>
      </div>
    </Card>
  );
}
