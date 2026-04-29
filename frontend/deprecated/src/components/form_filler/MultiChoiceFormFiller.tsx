import type { ChoiceContent } from "../node/questionTypes";
import { ExpandableSelector } from "../../index.optimized";

interface MultiChoiceFormFillerProps {
  question: ChoiceContent;
  value: string[];
  onChange: (nextValue: string[]) => void;
}

export function MultiChoiceFormFiller({
  question,
  value,
  onChange,
}: MultiChoiceFormFillerProps) {
  const isSingleSelect = question.definition.max === 1;

  function toggleOption(optionId: string) {
    const alreadySelected = value.includes(optionId);

    if (isSingleSelect) {
      onChange(alreadySelected ? [] : [optionId]);
      return;
    }

    if (alreadySelected) {
      onChange(value.filter((selectedId) => selectedId !== optionId));
      return;
    }

    if (value.length >= question.definition.max) {
      return;
    }

    onChange([...value, optionId]);
  }

  return (
    <div className="flex flex-col items-center gap-4.5">
      <div className="flex items-center justify-center gap-3 text-center">
        <span className="text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground">Choices</span>
        <span className="text-[0.8rem] text-muted-foreground">
          {isSingleSelect
            ? "Select one option"
            : `${question.definition.min} to ${question.definition.max} selections`}
        </span>
      </div>

      <div
        className="flex w-full flex-col items-center gap-3"
        role={isSingleSelect ? "radiogroup" : "group"}
        aria-label={question.title}
      >
        {question.definition.options.map((option) => {
          const isSelected = value.includes(option.id);
          const isDisabled = !isSelected && !isSingleSelect && value.length >= question.definition.max;

          return (
            <div
              key={option.id}
              role={isSingleSelect ? "radio" : "checkbox"}
              aria-checked={isSelected}
              aria-disabled={isDisabled}
              className="w-full max-w-2xl"
            >
              <ExpandableSelector
                value={option.label || option.id}
                onChange={() => {}}
                readOnly
                selected={isSelected}
                onSelect={isDisabled ? undefined : () => toggleOption(option.id)}
                className={isDisabled ? "opacity-50" : undefined}
                placeholder=""
                minHeightClassName="min-h-[50px]"
                maxHeightClassName="max-h-[170px]"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
