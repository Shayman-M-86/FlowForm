import type { ChoiceContent } from "../node/questionTypes";
import "../node/MultiChoiceQuestion.css";

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
    <div className="form-filler-question__body">
      <div className="node-pill__choice-range-wrapper">
        <span className="node-pill__choice-range-title">Choices</span>
        <span className="form-filler-multi-choice__range">
          {isSingleSelect
            ? "Select one option"
            : `${question.definition.min} to ${question.definition.max} selections`}
        </span>
      </div>

      <div className="node-pill__options form-filler-multi-choice__list" role={isSingleSelect ? "radiogroup" : "group"} aria-label={question.title}>
        {question.definition.options.map((option) => {
          const isSelected = value.includes(option.id);
          const isDisabled = !isSelected && !isSingleSelect && value.length >= question.definition.max;

          return (
            <div key={option.id} className="node-pill__option-row">
              <button
                type="button"
                className={`form-filler-multi-choice__button ${isSelected ? "form-filler-multi-choice__button--selected" : ""}`}
                aria-pressed={isSelected}
                disabled={isDisabled}
                onClick={() => toggleOption(option.id)}
              >
                <span className="form-filler-multi-choice__marker" aria-hidden="true">
                  {isSingleSelect ? (isSelected ? "●" : "○") : (isSelected ? "✓" : "+")}
                </span>
                <span className="form-filler-multi-choice__label">{option.label || option.id}</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
